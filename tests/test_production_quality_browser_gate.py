from tools.run_production_quality_browser_gate import build_post_deploy_result


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
