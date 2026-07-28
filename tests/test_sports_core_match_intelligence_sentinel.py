from __future__ import annotations

import shutil
from pathlib import Path

from engines.sentinel_autopilot_engine import (
    build_v944_match_center_foundation_contract_snapshot,
    create_autopilot_task,
    detect_product_quality_contract_issues,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL"


def _copy_contract(tmp_path: Path) -> None:
    for relative in (
        "app.py",
        "engines/api_football_live_tracker_engine.py",
        "engines/match_context_engine.py",
        "engines/sports_domain_model_engine.py",
        "engines/sports_knowledge_layer_engine.py",
        "engines/match_intelligence_engine.py",
        "engines/shark_context_presentation_engine.py",
        "engines/sports_platform_contracts.py",
        "engines/telegram_intelligence_engine.py",
        "static/v933-product.css",
        "templates/components/v944_match_center.html",
        "templates/match_detail.html",
    ):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def test_sentinel_opens_approval_task_if_unique_engine_contract_is_broken(
    tmp_path,
):
    _copy_contract(tmp_path)
    healthy = build_v944_match_center_foundation_contract_snapshot(
        tmp_path,
        VERSION,
    )
    assert healthy["validation_result"] == "PASS"
    assert healthy["evidence"]["match_intelligence_core_contract"] is True

    engine = tmp_path / "engines/match_intelligence_engine.py"
    source = engine.read_text(encoding="utf-8")
    engine.write_text(
        source.replace(
            'MATCH_INTELLIGENCE_CONTRACT = "MATCH-INTELLIGENCE-EVIDENCE-V1"',
            'MATCH_INTELLIGENCE_CONTRACT = "BROKEN-CONTRACT"',
        ),
        encoding="utf-8",
    )

    broken = build_v944_match_center_foundation_contract_snapshot(
        tmp_path,
        VERSION,
    )
    assert broken["validation_result"] == "REGRESSION"
    assert broken["evidence"]["match_intelligence_core_contract"] is False

    issues = detect_product_quality_contract_issues(tmp_path, VERSION)
    issue = next(
        item
        for item in issues
        if item["id"] == "V944-MATCH-CENTER-FOUNDATION-CONTRACT"
    )
    task = create_autopilot_task(issue)
    assert issue["priority"] == "P1"
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True
