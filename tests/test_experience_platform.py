from pathlib import Path

from engines.experience_platform_engine import (
    EXPERIENCE_AUDITOR_CONTRACT,
    EXPERIENCE_PLATFORM_CONTRACT,
    NAVIGATION_INTEGRITY_CONTRACT,
    PRODUCT_POLISH_CONTRACT,
    UX_CONSISTENCY_CONTRACT,
    VISUAL_DENSITY_CONTRACT,
    build_experience_platform_snapshot,
)
from engines.sports_platform_contracts import build_sports_platform_contract_registry
from engines.project_operating_system_engine import build_product_roadmap
from engines.sentinel_autopilot_engine import build_experience_platform_contract_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_experience_platform_scans_product_surfaces_without_side_effects():
    snapshot = build_experience_platform_snapshot(ROOT)

    assert snapshot["contract"] == EXPERIENCE_PLATFORM_CONTRACT
    assert snapshot["screen_count"] > 0
    assert snapshot["component_count"] > 0
    assert snapshot["routes_detected"] > 0
    assert snapshot["production_modified"] is False
    assert snapshot["browser_qa_required_before_ui_changes"] is True
    assert snapshot["autopilot_autofix_allowed"] is False
    assert all(value in (0, False) for value in snapshot["guardrails"].values())


def test_experience_platform_exposes_all_required_auditors():
    snapshot = build_experience_platform_snapshot(ROOT)
    auditors = snapshot["auditors"]

    assert auditors["experience_auditor"] == EXPERIENCE_AUDITOR_CONTRACT
    assert auditors["product_polish_engine"] == PRODUCT_POLISH_CONTRACT
    assert auditors["ux_consistency_checker"] == UX_CONSISTENCY_CONTRACT
    assert auditors["navigation_integrity_checker"] == NAVIGATION_INTEGRITY_CONTRACT
    assert auditors["visual_density_auditor"] == VISUAL_DENSITY_CONTRACT


def test_experience_platform_findings_are_review_items_not_autofixes():
    snapshot = build_experience_platform_snapshot(ROOT)
    polish = snapshot["audit"]["product_polish"]

    assert polish["autofix_allowed"] is False
    for finding in polish["top_findings"]:
        assert finding["requires_human_approval"] is True
        assert finding["autofix_allowed"] is False
        assert finding["screen"]
        assert finding["recommendation"]


def test_experience_platform_registry_roadmap_and_sentinel_are_updated():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    roadmap = build_product_roadmap(ROOT)
    roadmap_modules = {item["name"]: item for item in roadmap["modules"]}
    sentinel = build_experience_platform_contract_snapshot(ROOT)

    assert capabilities["experience_platform"]["state"] == "INTEGRATED"
    assert capabilities["experience_platform"]["contract"] == EXPERIENCE_PLATFORM_CONTRACT
    assert roadmap_modules["Experience Platform"]["state"] == "COMPLETED"
    assert sentinel["validation_result"] == "PASS"


def test_experience_platform_engine_stays_local_and_read_only():
    engine = (ROOT / "engines" / "experience_platform_engine.py").read_text(encoding="utf-8", errors="replace")

    import re

    unsafe_import_or_call = re.compile(
        r"^\s*(?:import|from)\s+(?:sqlite3|requests|urllib\.request|flask|stripe|openai|bs4|selenium|playwright|subprocess)\b|\b(?:commit|execute|executemany|urlopen|Session)\s*\(",
        re.IGNORECASE | re.MULTILINE,
    )
    assert not unsafe_import_or_call.search(engine)
    assert '"database_writes": 0' in engine
    assert '"external_calls": 0' in engine
    assert '"telegram_sends": 0' in engine
    assert '"stripe_calls": 0' in engine