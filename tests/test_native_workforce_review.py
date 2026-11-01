from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import engines.product_review_system_engine as ce
from engines.game_ui_review_lab import GAME_UI_REVIEW_TARGETS


NOW = "2026-10-29T01:00:00+01:00"


def _owned_storage(tmp_path, job_id="native-test-job"):
    storage = tmp_path / "runtime"
    storage.mkdir(exist_ok=True)
    (storage / "scheduler.lock").write_text(json.dumps({"job_id": job_id, "pid": os.getpid(), "locked_at_madrid": NOW}))
    return storage, job_id


def _write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _readonly(tmp_path):
    return ce.run_native_workforce_review(tmp_path, "TEST", now=NOW, write=False)


def test_native_review_missing_evidence_is_executed_unknown_without_business_claims(tmp_path):
    before = list(tmp_path.rglob("*"))
    result = _readonly(tmp_path)
    receipt = result["receipt"]
    assert result["ok"] is True and result["result"] == "PASS"
    assert receipt["expected_count"] == receipt["executed_count"] == 22
    assert receipt["outcome"] == "UNKNOWN"
    assert all(row["state"] == "UNKNOWN" for row in receipt["results"])
    assert receipt["browser_executed"] is False
    assert receipt["production_certified"] is False
    assert receipt["business_execution_certified"] is False
    assert receipt["autonomous_agents_started"] == receipt["external_calls"] == receipt["paid_credits_consumed"] == 0
    assert list(tmp_path.rglob("*")) == before
    assert set(ce.NATIVE_WORKFORCE_GAME_TARGETS) == set(GAME_UI_REVIEW_TARGETS)


def test_native_review_detects_mutated_membership_contract_and_binds_source_hash(tmp_path):
    path = "engines/membership_engine.py"
    clean = 'PLAN_ORDER={"FREE":0,"PRO":1,"ELITE":2,"ADMIN":3}\nFEATURE_MIN_PLAN={"premium":"PRO"}\nMEMBERSHIP_LIMITS={"FREE":{},"PRO":{},"ELITE":{},"ADMIN":{}}\n'
    _write(tmp_path, path, clean)
    first = _readonly(tmp_path)["receipt"]
    good = next(row for row in first["results"] if row["id"] == "membership_value")
    assert good["static_state"] == "PASS" and good["state"] == "UNKNOWN"
    _write(tmp_path, path, clean.replace('"premium":"PRO"', '"premium":"NONEXISTENT"'))
    second = _readonly(tmp_path)["receipt"]
    bad = next(row for row in second["results"] if row["id"] == "membership_value")
    assert bad["static_state"] == bad["state"] == "FAIL"
    assert bad["checks"][0]["result"] == "PLAN_REFERENCE_MISMATCH"
    assert good["source_fingerprint"] != bad["source_fingerprint"]
    assert first["source_fingerprint"] != second["source_fingerprint"]


def test_native_review_detects_inventory_contamination_without_counting_roles_as_workers(tmp_path):
    path = "templates/admin_company_os.html"
    _write(tmp_path, path, '<details class="v857-worker-card game-ui-discipline">Review</details>')
    receipt = _readonly(tmp_path)["receipt"]
    result = next(row for row in receipt["results"] if row["id"] == "admin_command_center")
    assert result["state"] == "FAIL"
    assert result["checks"][0]["result"] == "DISCIPLINE_CONTAMINATES_WORKER_INVENTORY"
    _write(tmp_path, path, '<details class="game-ui-discipline">Review</details>')
    result = next(row for row in _readonly(tmp_path)["receipt"]["results"] if row["id"] == "admin_command_center")
    assert result["static_state"] == "PASS" and result["state"] == "UNKNOWN"


def test_native_review_finite_json_guard_detects_missing_explicit_false():
    clean = "import json\ndef encode_snapshot(payload):\n return json.dumps(payload, allow_nan=False)\n"
    assert ce._nw_static_check("finite_json_contract", [clean])[0] == "PASS"
    assert ce._nw_static_check("finite_json_contract", [clean.replace("False", "True")])[0] == "FAIL"


def test_native_review_does_not_emit_source_text_or_read_outside_allowlist(tmp_path):
    marker = "PRIVATE_TEST_LITERAL_38910"
    _write(tmp_path, ".env", marker)
    _write(tmp_path, "app.py", "def broken(" + marker)
    result = _readonly(tmp_path)
    assert marker not in json.dumps(result)
    assert ".env" not in {item["path"] for item in result["receipt"]["sources"]}
    technical = next(row for row in result["receipt"]["results"] if row["id"] == "technical_director")
    # Missing other required input does not turn a partial checkout into proof
    # of a production syntax failure.
    assert technical["state"] == "UNKNOWN"
    _write(tmp_path, "engines/security_engine.py", "SAFE = True\n")
    technical = next(row for row in _readonly(tmp_path)["receipt"]["results"] if row["id"] == "technical_director")
    assert technical["state"] == "FAIL"


def test_native_review_source_bounds_and_symlink_escape(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("SECRET = 'outside'\n")
    (root / "app.py").symlink_to(outside)
    _write(root, "templates/base.html", "x" * 100)
    monkeypatch.setattr(ce, "NATIVE_WORKFORCE_MAX_SOURCE_BYTES", 64)
    snapshot, evidence, total = ce._nw_read_sources(root.resolve(), ce._nw_clock() + 2)
    assert snapshot["app.py"] is None and evidence["app.py"]["state"] == "OUTSIDE_PROJECT"
    assert snapshot["templates/base.html"] is None and evidence["templates/base.html"]["state"] == "INPUT_LIMIT"
    assert total <= 64


def test_native_budget_exhaustion_never_credits_unattempted_reviews(tmp_path, monkeypatch):
    ticks = iter([0.0] + [10.0] * 200)
    monkeypatch.setattr(ce, "_nw_clock", lambda: next(ticks))
    result = _readonly(tmp_path)
    assert result["result"] == "PARTIAL"
    assert result["receipt"]["expected_count"] == 22
    assert result["receipt"]["executed_count"] == 0
    assert not any(row["executed"] for row in result["receipt"]["results"])
    assert result["duration_ms"] == 10000
    assert result["receipt"]["limits"]["budget_exhausted"] is True


def test_native_write_requires_same_job_and_process_lock(tmp_path):
    storage, job = _owned_storage(tmp_path)
    with pytest.raises(RuntimeError, match="owned_scheduler_lock"):
        ce.run_native_workforce_review(tmp_path, storage_root=storage, job_id="another-job", now=NOW)
    (storage / "scheduler.lock").write_text(json.dumps({"job_id": job, "pid": os.getpid() + 1}))
    with pytest.raises(RuntimeError, match="owned_scheduler_lock"):
        ce.run_native_workforce_review(tmp_path, storage_root=storage, job_id=job, now=NOW)
    assert not (storage / "native_workforce").exists()


def test_native_persistence_keeps_unrelated_memory_and_loader_is_read_only(tmp_path):
    storage, job = _owned_storage(tmp_path)
    unrelated = b'{"recommendations":{"unrelated":{"state":"DEFERRED"}}}'
    (storage / "product_memory.json").write_bytes(unrelated)
    result = ce.run_native_workforce_review(tmp_path, storage_root=storage, job_id=job, now=NOW)
    path = storage / "native_workforce" / "state.json"
    written = path.read_bytes()
    loaded = ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=NOW)
    assert loaded["state"] == "RECENT"
    assert loaded["receipt"]["receipt_id"] == result["run_id"]
    assert path.read_bytes() == written
    assert (storage / "product_memory.json").read_bytes() == unrelated
    assert not (storage / "latest_snapshot.json").exists()


def test_native_loader_before_first_run_stale_future_and_revision_change(tmp_path, monkeypatch):
    storage = tmp_path / "runtime"
    assert ce.load_native_workforce_receipt(tmp_path, storage_root=storage)["state"] == "NOT_RUN"
    assert not storage.exists()
    storage, job = _owned_storage(tmp_path)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)
    ce.run_native_workforce_review(tmp_path, storage_root=storage, job_id=job, now=NOW)
    assert ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=NOW)["state"] == "RECENT"
    later = datetime.fromisoformat(NOW) + timedelta(hours=3)
    stale = ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=later)
    assert stale["state"] == "STALE" and stale["results"] == []
    earlier = datetime.fromisoformat(NOW) - timedelta(minutes=5)
    assert ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=earlier)["state"] == "CLOCK_UNVERIFIED"
    monkeypatch.setenv("RENDER_GIT_COMMIT", "b" * 40)
    changed = ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=NOW)
    assert changed["state"] == "STALE" and changed["reason"] == "SOURCE_REVISION_CHANGED"
    assert changed["results"] == []
    assert changed["receipt"]["source_revision_verified"] is False


def test_native_same_second_daily_ingestion_keeps_specific_proposals(tmp_path, monkeypatch):
    storage, job = _owned_storage(tmp_path)
    ce.run_native_workforce_review(tmp_path, storage_root=storage, job_id=job, now=NOW)
    monkeypatch.setattr(ce, "run_native_workforce_review", lambda *args, **kwargs: pytest.fail("daily must not execute reviews again"))
    findings, coverage = ce._nw_daily_findings(tmp_path, storage, datetime.fromisoformat(NOW))
    assert coverage["state"] == "RECENT" and coverage["executed_count"] == 22
    technical_art = next(item for item in findings if item["check_id"] == "technical_art")
    assert "oclusión" in technical_art["proposal"]
    assert technical_art["evidence_sufficient"] is False
    assert all(item["automatic_execution_allowed"] is False for item in findings)
    original_id = ce._ce_recommendation_id(technical_art)
    assert ce._ce_recommendation_id({**technical_art, "proposal": "Una revisión humana precisa de la misma comprobación."}) == original_id


def test_native_history_bounded_dedup_decisions_preserved_and_unknown_never_resolves(tmp_path):
    receipt = _readonly(tmp_path)["receipt"]
    state = {"contract": ce.NATIVE_WORKFORCE_MEMORY_CONTRACT}
    for index in range(51):
        sample = {**receipt, "receipt_id": "NWR-" + format(index, "016x")}
        state = ce._nw_update_state(state, sample)
    assert len(state["history"]) == 48
    assert len(state["proposals"]) == 22
    assert state["proposals"]["membership_value"]["seen_count"] == 51
    item = state["proposals"]["membership_value"]
    item.update({"state": "DEFERRED", "decisions": [{"reason": "Revisión humana pendiente"}]})
    deferred = ce._nw_update_state(state, receipt)["proposals"]["membership_value"]
    assert deferred["state"] == "DEFERRED" and deferred["decisions"] == item["decisions"]
    item["state"] = "VERIFIED"
    unknown = ce._nw_update_state(state, receipt)["proposals"]["membership_value"]
    assert unknown["state"] == "VERIFIED" and unknown["reopened_count"] == 0
    changed = copy.deepcopy(receipt)
    next(row for row in changed["results"] if row["id"] == "membership_value")["state"] = "FAIL"
    failed = ce._nw_update_state(state, changed)["proposals"]["membership_value"]
    assert failed["state"] == "REGRESSED" and failed["reopened_count"] == 1


def test_native_daily_memory_does_not_resolve_absent_or_reopen_unknown_scoped_records():
    now = NOW
    memory = ce._ce_default_memory(now)
    memory["recommendations"]["native"] = {"source_family": "native_workforce", "state": "IMPLEMENTED", "missed_count": 3}
    updated = ce._ce_update_memory(memory, [], {}, "r", "s", now, {})
    assert updated["recommendations"]["native"] == memory["recommendations"]["native"]
    candidate = {"recommendation_id": "native", "component": "native_workforce.product_ceo", "evidence_sufficient": False,
                 "evidence": "STATIC_PARTIAL", "priority": "P3", "issue_status": "INSUFFICIENT_EVIDENCE"}
    updated = ce._ce_update_memory(updated, [candidate], {}, "r2", "s2", now, {})
    assert updated["recommendations"]["native"]["state"] == "IMPLEMENTED"
    assert not updated["recommendations"]["native"].get("resolved_at")


def test_native_invalid_persisted_receipt_never_promotes_or_overwrites_history(tmp_path):
    storage, job = _owned_storage(tmp_path)
    path = storage / "native_workforce" / "state.json"
    path.parent.mkdir()
    path.write_text("{incomplete")
    before = path.read_bytes()
    assert ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=NOW)["state"] == "UNAVAILABLE"
    with pytest.raises(ValueError):
        ce.run_native_workforce_review(tmp_path, storage_root=storage, job_id=job, now=NOW)
    assert path.read_bytes() == before
    receipt = _readonly(tmp_path)["receipt"]
    receipt["production_certified"] = True
    path.write_text(json.dumps({"contract": ce.NATIVE_WORKFORCE_MEMORY_CONTRACT, "latest": receipt}))
    assert ce.load_native_workforce_receipt(tmp_path, storage_root=storage, now=NOW)["state"] == "UNAVAILABLE"
