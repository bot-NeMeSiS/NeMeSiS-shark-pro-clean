from __future__ import annotations

import json
from pathlib import Path

from engines.product_review_system_engine import (
    CONTINUOUS_EVOLUTION_OS_CONTRACT,
    DAILY_PRODUCT_SNAPSHOT_CONTRACT,
    PRODUCT_MEMORY_CONTRACT,
    build_continuous_evolution_status_snapshot,
    load_product_memory,
    record_continuous_evolution_decision,
    run_continuous_evolution_cycle,
    run_continuous_evolution_scheduler_task,
)

ROOT = Path(__file__).resolve().parents[1]


def test_continuous_evolution_three_runs_detect_stable_and_new_change(tmp_path):
    storage = tmp_path / "ceos"
    run1 = run_continuous_evolution_cycle(ROOT, "TEST", now="2026-08-11T09:00:00+02:00", storage_root=storage)
    run2 = run_continuous_evolution_cycle(ROOT, "TEST", now="2026-08-11T09:10:00+02:00", storage_root=storage)
    run3 = run_continuous_evolution_cycle(
        ROOT,
        "TEST",
        now="2026-08-11T09:20:00+02:00",
        storage_root=storage,
        control_fixture={
            "id": "SIM-CEOS-NEW-FRICTION",
            "module": "Founder Center",
            "screen": "admin_founder_dashboard.html",
            "route": "/admin/founder-dashboard",
            "component": "continuous_evolution_fixture",
            "evidence": "SIMULATED_QA: nuevo cambio controlado para validar deteccion temporal.",
            "priority": "P2",
            "proposal": "Mantener la simulacion fuera de datos reales y registrar NEW correctamente.",
        },
    )

    assert run1["snapshot"]["contract"] == DAILY_PRODUCT_SNAPSHOT_CONTRACT
    assert run1["snapshot"]["temporal_comparison"]["today_vs_previous"]["state"] == "INSUFFICIENT_HISTORY"
    assert run2["snapshot"]["temporal_comparison"]["today_vs_previous"]["new"] == []
    assert run2["snapshot"]["temporal_comparison"]["today_vs_previous"]["state"] == "UNCHANGED"
    assert run3["snapshot"]["temporal_comparison"]["today_vs_previous"]["new"]
    assert run3["snapshot"]["evidence_origin"] == "SIMULATED_QA"

    memory = load_product_memory(ROOT, storage_root=storage)
    assert memory["contract"] == PRODUCT_MEMORY_CONTRACT
    assert len(memory["snapshots"]) == 3
    assert memory["learning_summary"]["history_storage"] is True
    assert memory["learning_summary"]["actual_learning"] is True
    assert all(item["snapshot_id"] for item in memory["snapshots"])


def test_continuous_evolution_restart_reads_existing_memory_and_latest_snapshot(tmp_path):
    storage = tmp_path / "ceos"
    first = run_continuous_evolution_cycle(ROOT, "TEST", now="2026-08-11T10:00:00+02:00", storage_root=storage)
    latest_path = storage / "latest_snapshot.json"
    memory_path = storage / "product_memory.json"

    assert latest_path.exists()
    assert memory_path.exists()

    status = build_continuous_evolution_status_snapshot(ROOT, "TEST", storage_root=storage, now="2026-08-11T10:05:00+02:00")
    assert status["status"] == "OBSERVED"
    assert status["latest_snapshot_id"] == first["snapshot"]["snapshot_id"]
    assert status["product_memory"]["recommendations"] > 0
    assert status["founder_brief"]["contract"]
    assert status["prepared_for_codex"]["ready_count"] > 0

    stored = json.loads(latest_path.read_text(encoding="utf-8"))
    assert stored["production_modified"] is False
    assert stored["telegram_sent"] is False
    assert stored["stripe_called"] is False


def test_continuous_evolution_scheduler_is_local_safe_and_idempotent(tmp_path):
    storage = tmp_path / "ceos"
    scheduled = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T11:00:00+02:00", storage_root=storage)
    repeated = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T11:05:00+02:00", storage_root=storage)

    assert scheduled["ok"] is True
    assert scheduled["result"] == "PASS"
    assert scheduled["cycle"]["run"]["execution_mode"] == "scheduled_run"
    assert scheduled["dangerous_actions_executed"] is False
    assert repeated["ok"] is True
    assert repeated["result"] == "SKIPPED_NOT_DUE"
    task_state = repeated["scheduler"]["tasks"]["daily_product_review"]
    assert task_state["run_count"] == 1
    assert task_state["automated_or_manual"] == "scheduled_run"
    assert task_state["next_expected_run"]


def test_continuous_evolution_decision_transitions_are_traceable(tmp_path):
    storage = tmp_path / "ceos"
    result = run_continuous_evolution_cycle(ROOT, "TEST", now="2026-08-11T12:00:00+02:00", storage_root=storage)
    rec_id = result["snapshot"]["recommendations"][0]["recommendation_id"]
    decision = record_continuous_evolution_decision(ROOT, rec_id, "DEFERRED", "No se toca antes de cerrar LRM-001.", storage_root=storage, now="2026-08-11T12:05:00+02:00")
    memory = load_product_memory(ROOT, storage_root=storage)

    assert decision["ok"] is True
    assert memory["recommendations"][rec_id]["state"] == "DEFERRED"
    assert memory["recommendations"][rec_id]["decisions"][0]["reason"] == "No se toca antes de cerrar LRM-001."
    assert any(event["type"] == "HUMAN_DECISION" for event in memory["events"])


def test_continuous_evolution_guardrails_for_codex_briefs(tmp_path):
    storage = tmp_path / "ceos"
    result = run_continuous_evolution_cycle(ROOT, "TEST", now="2026-08-11T13:00:00+02:00", storage_root=storage)
    inbox = result["snapshot"]["prepared_for_codex"]

    assert result["snapshot"]["continuous_evolution_contract"] == CONTINUOUS_EVOLUTION_OS_CONTRACT
    assert inbox["ready_count"] > 0
    first = next(item for item in inbox["items"] if item["state"] == "READY")
    assert first["approved_by_founder"] is False
    assert first["automatic_execution_allowed"] is False
    assert first["evidence"] not in {"none", "todo", ""}
    assert "Sports Core" in " ".join(first["modules_not_to_touch"])
