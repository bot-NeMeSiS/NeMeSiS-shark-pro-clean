from pathlib import Path

import pytest

from tools.run_production_quality_browser_gate import _visual_asset_contract, build_post_deploy_result
from tools.run_production_quality_browser_gate import classify_browser_resources


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


def resource_case(*, fallback=True, url="https://cdn.example.invalid/team/badge/crest.png"):
    block = {"url": url, "method": "GET", "reason": "BLOCKED_BY_QA_POLICY"}
    request = {"url": url, "method": "GET", "error": "net::ERR_FAILED", "type": "image"}
    console = {"url": url, "text": "Failed to load resource: net::ERR_FAILED"}
    image = {"url": url, "kind": "TEAM_CREST", "fallback_working": fallback}
    return block, request, console, image


def test_policy_abort_requires_observed_working_fallback():
    block, request, console, image = resource_case()
    result = classify_browser_resources("https://example.invalid", [block], [request], [console], [image])
    assert result["subresources_and_fallbacks"] == "PASS"
    assert result["policy_console"] == [console]
    assert result["unexplained_console"] == []
    assert result["images"][0]["classification"] == "QA_BLOCKED_EXTERNAL"
    assert "classification" not in image


def test_chromium_inspector_suffix_still_requires_recorded_policy_abort():
    block, request, console, image = resource_case()
    request["error"] = "net::ERR_BLOCKED_BY_CLIENT.Inspector"
    console["text"] = "Failed to load resource: " + request["error"]
    result = classify_browser_resources("https://example.invalid", [block], [request], [console], [image])
    assert result["unexplained_console"] == []
    assert result["subresources_and_fallbacks"] == "PASS"
    without_proof = classify_browser_resources("https://example.invalid", [], [request], [console], [image])
    assert without_proof["unexplained_console"] == [console]


@pytest.mark.parametrize("phase,status,received,expected", [
    ("QA_NAVIGATION", 200, 3, "PASS"),
    ("CRITICAL_PAGE", 200, 3, "FAIL"),
    ("UNKNOWN", 200, 3, "FAIL"),
    ("QA_NAVIGATION", 404, 3, "FAIL"),
    ("QA_NAVIGATION", 200, 1, "FAIL"),
])
def test_navigation_abort_requires_proven_subsequent_success(phase, status, received, expected):
    url = "https://example.invalid/static/brand.webp"
    request = {"url": url, "method": "GET", "error": "net::ERR_ABORTED", "type": "image", "phase": phase, "failed_at": 2}
    response = {"url": url, "status": status, "received_at": received}
    result = classify_browser_resources("https://example.invalid", [], [request], [], [], [response])
    assert result["subresources_and_fallbacks"] == expected


@pytest.mark.parametrize("fallback,expected", [(False, "FAIL"), (None, "NOT_RUN")])
def test_broken_or_unobserved_fallback_never_passes(fallback, expected):
    block, request, console, image = resource_case(fallback=fallback)
    result = classify_browser_resources("https://example.invalid", [block], [request], [console], [image])
    assert result["subresources_and_fallbacks"] == expected


@pytest.mark.parametrize("missing", ["block", "request", "reason", "method"])
def test_console_exoneration_requires_matching_abort_provenance(missing):
    block, request, console, image = resource_case()
    if missing == "reason":
        block["reason"] = "UNVERIFIED"
    if missing == "method":
        block["method"] = "POST"
    result = classify_browser_resources("https://example.invalid", [] if missing == "block" else [block],
        [] if missing == "request" else [request], [console], [image])
    assert result["unexplained_console"] == [console]
    assert result["subresources_and_fallbacks"] == "NOT_RUN"


@pytest.mark.parametrize("text", ["Uncaught TypeError: broken", "Failed to load resource: the server responded with a status of 404", "Failed to load resource: net::ERR_CERT_AUTHORITY_INVALID"])
def test_policy_does_not_hide_other_errors_at_same_url(text):
    block, request, console, image = resource_case()
    console["text"] = text
    result = classify_browser_resources("https://example.invalid", [block], [request], [console], [image])
    assert result["unexplained_console"] == [console]


@pytest.mark.parametrize("kind", ["BRAND_ASSET", "APP_ICON"])
def test_required_identity_image_failure_is_not_exempted(kind):
    block, request, console, image = resource_case()
    image["kind"] = kind
    result = classify_browser_resources("https://example.invalid", [block], [request], [console], [image])
    assert result["subresources_and_fallbacks"] == "FAIL"


@pytest.mark.parametrize("kind", ["image", "script", "stylesheet", "font"])
def test_local_asset_failure_remains_failure_even_if_policy_blocked(kind):
    block, request, console, image = resource_case(url="https://example.invalid/static/required.asset")
    request["type"] = kind
    result = classify_browser_resources("https://example.invalid", [block], [request], [console], [])
    assert result["subresources_and_fallbacks"] == "FAIL"
    assert result["required_asset_failures"] == [request]


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
        "https://example.invalid/static/img/nemesis-shark-atmosphere-v2.webp?v=design4-atmosphere-1",
    ])
    assert passed is True
    assert evidence == {
        "brand_shark_loaded": True,
        "atmospheric_shark_loaded": True,
        "legacy_shark_loaded": False,
    }

    legacy_passed, legacy_evidence = _visual_asset_contract([
        "https://example.invalid/static/img/nemesis-shark-brand.svg",
        "https://example.invalid/static/img/nemesis-shark-atmosphere-v2.webp",
        "https://example.invalid/static/img/shark-logo.svg",
    ])
    assert legacy_passed is False
    assert legacy_evidence["legacy_shark_loaded"] is True


def test_production_quality_gate_can_use_an_installed_browser():
    source = (Path(__file__).parents[1] / "tools" / "run_production_quality_browser_gate.py").read_text(encoding="utf-8")

    assert 'parser.add_argument("--browser-executable", default="")' in source
    assert 'launch_options["executable_path"]' in source
