from pathlib import Path

from tools.run_production_quality_browser_gate import _visual_asset_contract, build_post_deploy_result


CHECKS = {
    "health": "PASS",
    "sha_alignment": "PASS",
    "logs_recent": "PASS",
    "critical_routes": "PASS",
    "topbar_click_journey": "PASS",
    "mobile_nav": "PASS",
    "sports_truth": "PASS",
    "temporal_context": "PASS",
    "performance_sample": "PASS",
    "critical_visual_surfaces": "PASS",
    "client_admin_protection": "PASS",
}


def test_production_quality_gate_certifies_only_complete_pass():
    result = build_post_deploy_result(
        expected_sha="a" * 40,
        actual_sha="a" * 40,
        checks=CHECKS,
        evidence={},
    )
    assert result["result"] == "PRODUCTION_CERTIFIED"
    assert result["rollback_recommended"] is False
    assert result["production_mutations"] == 0


def test_production_quality_gate_recommends_rollback_for_regression():
    checks = dict(CHECKS)
    checks["topbar_click_journey"] = "FAIL"
    result = build_post_deploy_result(
        expected_sha="a" * 40,
        actual_sha="a" * 40,
        checks=checks,
        evidence={},
    )
    assert result["result"] == "REGRESSION_DETECTED"
    assert result["rollback_recommended"] is True


def test_production_quality_gate_blocks_missing_evidence():
    checks = dict(CHECKS)
    checks["logs_recent"] = "NOT_RUN"
    result = build_post_deploy_result(
        expected_sha="a" * 40,
        actual_sha="a" * 40,
        checks=checks,
        evidence={},
    )
    assert result["result"] == "BLOCKED"
    assert result["missing_checks"] == ["logs_recent"]


def test_production_visual_contract_requires_two_current_sharks_and_rejects_legacy():
    passed, evidence = _visual_asset_contract([
        "https://example.invalid/static/img/nemesis-shark-brand.svg?v=official16-brand-2",
        "https://example.invalid/static/img/nemesis-shark-atmosphere.svg?v=official16-atmosphere-3",
    ])
    assert passed is True
    assert evidence == {
        "brand_shark_loaded": True,
        "atmospheric_shark_loaded": True,
        "legacy_shark_loaded": False,
    }

    legacy_passed, legacy_evidence = _visual_asset_contract([
        "https://example.invalid/static/img/nemesis-shark-brand.svg",
        "https://example.invalid/static/img/nemesis-shark-atmosphere.svg",
        "https://example.invalid/static/img/shark-logo.svg",
    ])
    assert legacy_passed is False
    assert legacy_evidence["legacy_shark_loaded"] is True


def test_production_quality_gate_can_use_an_installed_browser():
    source = (Path(__file__).parents[1] / "tools" / "run_production_quality_browser_gate.py").read_text(encoding="utf-8")

    assert 'parser.add_argument("--browser-executable", default="")' in source
    assert 'launch_options["executable_path"]' in source
