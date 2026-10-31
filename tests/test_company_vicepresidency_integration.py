"""Vicepresidency integration: same receipt, read-only Admin projection."""
from __future__ import annotations

from pathlib import Path
from engines.company_vicepresidency_engine import READOUT_CONTRACT, CONTRACT


def test_native_hourly_review_contains_executive_readout(tmp_path):
    from engines.product_review_system_engine import run_native_workforce_review
    result = run_native_workforce_review(
        project_root=tmp_path, app_version="QA_ONLY", write=False,
        now="2026-10-31T13:00:00+01:00",
    )
    receipt = result["receipt"]
    vp = receipt["vicepresidency_readout"]
    assert vp["contract"] == READOUT_CONTRACT
    assert vp["receipt_id"] == receipt["receipt_id"]
    assert vp["executed"] == sum(x["executed"] is True for x in receipt["results"])
    assert vp["external_calls"] == vp["paid_credits_consumed"] == 0
    assert vp["independent_votes"] == 0
    assert vp["production_certified"] is False
    assert vp["automatic_changes_authorized"] is False


def test_company_os_shows_existing_receipt_without_starting_workers(monkeypatch, tmp_path):
    import engines.product_review_system_engine as review_engine
    import engines.game_ui_review_lab as game_lab
    import engines.company_workforce_receipts_engine as cron_receipts
    from engines.company_operating_system_engine import build_company_os_summary

    fake = {
        "contract": "NEMESIS-NATIVE-WORKFORCE-REVIEW-V1",
        "receipt_id": "NWR-qa-only",
        "finished_at_madrid": "2026-10-31T13:00:00+01:00",
        "results": [
            {"id": "technical_director", "worker_name": "Technical Director Worker",
             "executed": True, "state": "UNKNOWN"},
            {"id": "game_motion", "executed": True, "state": "UNKNOWN"},
        ],
    }
    monkeypatch.setattr(
        review_engine, "load_native_workforce_receipt",
        lambda *args, **kwargs: {
            "state": "RECENT", "receipt": fake, "results": fake["results"],
        },
    )
    monkeypatch.setattr(
        game_lab, "build_game_ui_lab",
        lambda **kwargs: {
            "disciplines": [{"id": "game_motion", "name": "Motion", "acceptance": "Accesible"}],
            "reviewed_count": 1,
        },
    )
    monkeypatch.setattr(
        cron_receipts, "master_cron_receipt",
        lambda path: {
            "state": "RECENT_RECEIPT",
            "last_observed_madrid": "2026-10-31T13:00:00+01:00",
        },
    )
    summary = build_company_os_summary(
        "QA_ONLY", runtime={"db_path": str(tmp_path / "absent-db.sqlite")},
        project_root=tmp_path, storage_root=tmp_path,
    )
    board = summary["vicepresidency"]
    assert board["contract"] == CONTRACT
    assert board["president"]["retains_control"]
    assert board["vicepresident"]["state"] == "RECENT_STATIC_COORDINATION"
    assert board["cron"]["state"] == "RECENT_RECEIPT"
    assert board["reviewed_static_specialists"] >= 2
    assert board["crosscheck"]["independent_votes"] == 0
    assert len(board["advisory_council"]) == 10
    assert not board["vicepresident"]["can_approve_external_changes"]
    assert board["production_mutations"] == 0
    assert not (tmp_path / "absent-db.sqlite").exists()


def test_admin_template_has_no_power_grant_or_side_effect():
    from jinja2 import Environment
    root = Path(__file__).resolve().parents[1]
    page = (root / "templates" / "admin_company_os.html").read_text(encoding="utf-8")
    Environment().parse(page)
    assert 'id="vicepresidency"' in page
    assert "summary.vicepresidency" in page
    assert "president.retains_control" in page
    assert "No hay prioridades recientes verificables" in page
