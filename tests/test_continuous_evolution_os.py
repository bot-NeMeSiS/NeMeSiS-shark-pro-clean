from __future__ import annotations

import json
from pathlib import Path

from engines.product_review_system_engine import (
    CONTINUOUS_EVOLUTION_OS_CONTRACT,
    DAILY_PRODUCT_SNAPSHOT_CONTRACT,
    PRODUCT_MEMORY_CONTRACT,
    build_continuous_evolution_status_snapshot,
    load_product_memory,
    preview_continuous_evolution_scheduler_task,
    record_continuous_evolution_decision,
    run_continuous_evolution_cycle,
    run_continuous_evolution_scheduler_task,
    run_continuous_evolution_three_day_certification,
    run_safe_continuous_evolution_runner,
    set_continuous_evolution_pause,
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



def test_continuous_evolution_three_day_scheduled_certification(tmp_path):
    storage = tmp_path / "ceos"
    day1 = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:00:00+02:00", storage_root=storage)
    repeat = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:05:00+02:00", storage_root=storage)
    day2 = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-12T04:00:00+02:00", storage_root=storage)
    day3 = run_continuous_evolution_scheduler_task(
        ROOT,
        "TEST",
        task_name="daily_product_review",
        now="2026-08-13T04:00:00+02:00",
        storage_root=storage,
        control_fixture={"simulated_persona": "MOBILE", "simulated_metrics": {"friction_indicators": 2}},
    )
    status = build_continuous_evolution_status_snapshot(ROOT, "TEST", storage_root=storage, now="2026-08-13T04:10:00+02:00")
    memory = load_product_memory(ROOT, storage_root=storage)

    assert day1["result"] == "PASS"
    assert repeat["result"] == "SKIPPED_NOT_DUE"
    assert day2["result"] == "PASS"
    assert day3["result"] == "PASS"
    assert status["snapshot_count"] == 3
    assert status["cycles_completed"] == 3
    assert status["scheduler"]["tasks"]["daily_product_review"]["run_count"] == 3
    assert status["scheduler"]["tasks"]["daily_founder_brief"]["run_count"] == 3
    assert status["founder_brief"]["text"].startswith("FOUNDER BRIEF")
    assert len(memory["snapshots"]) == 3
    assert memory["learning_summary"]["actual_learning"] is True
    assert day3["cycle"]["snapshot"]["simulated_user_nightly_check"]["summary"]["worsened"] >= 1


def test_continuous_evolution_concurrent_lock_skips_existing_run(tmp_path):
    storage = tmp_path / "ceos"
    storage.mkdir(parents=True)
    (storage / "scheduler.lock").write_text('{"job_id":"JOB-ACTIVE","locked_at_madrid":"2026-08-11T04:00:00+02:00"}', encoding="utf-8")

    result = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:05:00+02:00", storage_root=storage)

    assert result["result"] == "SKIPPED_ALREADY_RUNNING"
    assert result["job"]["status"] == "SKIPPED_ALREADY_RUNNING"
    assert result["dangerous_actions_executed"] is False


def test_continuous_evolution_pause_resume_controls_scheduled_only(tmp_path):
    storage = tmp_path / "ceos"
    pause = set_continuous_evolution_pause(ROOT, paused=True, actor="test-admin", reason="qa pause", storage_root=storage, now="2026-08-11T03:00:00+02:00")
    scheduled = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:00:00+02:00", storage_root=storage)
    manual = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:05:00+02:00", storage_root=storage, force=True, trigger="MANUAL")
    resume = set_continuous_evolution_pause(ROOT, paused=False, actor="test-admin", reason="qa resume", storage_root=storage, now="2026-08-11T05:00:00+02:00")
    next_day = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-12T04:00:00+02:00", storage_root=storage)

    assert pause["control"]["paused"] is True
    assert scheduled["result"] == "SKIPPED_PAUSED"
    assert manual["result"] == "PASS"
    assert resume["control"]["paused"] is False
    assert next_day["result"] == "PASS"


def test_continuous_evolution_failure_recovery_preserves_last_good_state(tmp_path):
    storage = tmp_path / "ceos"
    good = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:00:00+02:00", storage_root=storage)
    failed = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-12T04:00:00+02:00", storage_root=storage, control_fixture={"scheduler_exception": True})
    status = build_continuous_evolution_status_snapshot(ROOT, "TEST", storage_root=storage)

    assert good["result"] == "PASS"
    assert failed["result"] == "PARTIAL"
    assert status["latest_snapshot_id"] == good["cycle"]["snapshot"]["snapshot_id"]
    assert status["cycles_failed"] == 1


def test_continuous_evolution_component_unavailable_is_partial_with_memory(tmp_path):
    storage = tmp_path / "ceos"
    result = run_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:00:00+02:00", storage_root=storage, control_fixture={"component_unavailable": "Product Review"})
    memory = load_product_memory(ROOT, storage_root=storage)

    assert result["result"] == "PARTIAL"
    assert result["cycle"]["snapshot"]["result"] == "PARTIAL_WITH_UNAVAILABLE_COMPONENTS"
    assert result["cycle"]["snapshot"]["components_unavailable"][0]["component"] == "Product Review"
    assert memory["contract"] == PRODUCT_MEMORY_CONTRACT
    assert memory["snapshots"]


def test_continuous_evolution_scheduler_timezone_week_month_and_runner(tmp_path):
    storage = tmp_path / "ceos"
    daily_before = preview_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T02:00:00+02:00", storage_root=storage)
    daily_after = preview_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="daily_product_review", now="2026-08-11T04:00:00+02:00", storage_root=storage)
    weekly = preview_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="weekly_executive_review", now="2026-08-17T04:30:00+02:00", storage_root=storage)
    monthly = preview_continuous_evolution_scheduler_task(ROOT, "TEST", task_name="monthly_strategy_review", now="2026-09-01T05:00:00+02:00", storage_root=storage)
    dry = run_safe_continuous_evolution_runner(ROOT, "TEST", task_name="daily_product_review", dry_run=True, now="2026-08-11T04:00:00+02:00", storage_root=storage)

    assert daily_before["due"] is False
    assert daily_after["due"] is True
    assert weekly["due"] is True
    assert monthly["due"] is True
    assert dry["dry_run"] is True
    assert dry["guardrails"]["NO_TELEGRAM"] is True
    assert dry["guardrails"]["NO_STRIPE"] is True



def test_continuous_evolution_three_day_certification_helper(tmp_path):
    result = run_continuous_evolution_three_day_certification(ROOT, "TEST", storage_root=tmp_path / "ceos", start_date="2026-08-11")

    assert result["contract"].endswith("3-DAY-CERTIFICATION-V1")
    assert result["status"] == "PASS"
    assert result["snapshot_count"] == 3
    assert all(item["result"] == "PASS" for item in result["runs"])
    assert all(item["result"] == "SKIPPED_NOT_DUE" for item in result["repeat_checks"])
    assert result["founder_brief_ready"] is True
    assert result["dangerous_actions_executed"] is False
