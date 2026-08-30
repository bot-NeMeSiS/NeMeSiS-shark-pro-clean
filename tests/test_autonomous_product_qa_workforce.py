from __future__ import annotations

from pathlib import Path

from engines.autonomous_product_qa_engine import (
    build_autonomous_product_qa_status,
    detect_product_qa_issues,
    product_qa_review_findings,
    record_product_qa_run,
    set_product_qa_pause,
)
from engines.sentinel_issues_engine import normalize_sentinel_issue, upsert_sentinel_issues


def failing_observation() -> dict:
    return {
        "production_sha": "fixture-sha",
        "evidence_complete": True,
        "navigation_clicks": [
            {
                "screen": "/app",
                "viewport": "desktop_1366x768",
                "element": "Partidos",
                "expected_path": "/calendar",
                "actual_path": "/app",
                "clicked": False,
                "hit_target": False,
                "http_status": 200,
                "page_ready": True,
            }
        ],
        "sports_truth": {
            "screen": "/",
            "confirmed_live_count": 0,
            "displayed_live_count": 2,
            "ft_rendered_live": 1,
        },
        "sports_knowledge": {
            "screen": "/match/m-1",
            "lineup_confirmed": True,
            "lineup_player_links": 0,
            "summary_ai_calls": 1,
            "summary_unsupported_claims": 1,
            "unsafe_media_visible": 1,
        },
        "client_copy": {
            "screen": "/live",
            "visible_text": "Provider cache hit. Próxima revisión en 180 s.",
        },
        "visual": {
            "shark": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "DRIFT", "evidence": "legacy shark marker"},
            "background": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MAJOR_DRIFT", "evidence": "flat background"},
        },
        "density": {"screen": "/app", "viewport": "desktop_1366x768", "first_viewport_product": False, "nested_panel_depth": 4},
        "mobile": {"screen": "/app", "viewport": "mobile_390x844", "overflow": True},
        "runtime": {"js_errors": ["TypeError: blocked topbar"], "broken_images": ["/static/img/missing.png"]},
        "journeys": [{"journey": "sports", "route": "/app", "expected": "/match/", "actual": "/app", "pass": False}],
    }


def clean_observation() -> dict:
    return {
        "production_sha": "clean-sha",
        "evidence_complete": True,
        "navigation_clicks": [
            {
                "screen": "/app",
                "viewport": "desktop_1366x768",
                "element": "Partidos",
                "expected_path": "/calendar",
                "actual_path": "/calendar",
                "clicked": True,
                "hit_target": True,
                "http_status": 200,
                "page_ready": True,
            }
        ],
        "sports_truth": {"screen": "/", "confirmed_live_count": 0, "displayed_live_count": 0, "ft_rendered_live": 0},
        "sports_knowledge": {"screen": "/match/m-1", "lineup_confirmed": True, "lineup_player_links": 1, "summary_ai_calls": 0, "summary_unsupported_claims": 0, "unsafe_media_visible": 0},
        "client_copy": {"screen": "/live", "visible_text": "No hay partidos en directo."},
        "visual": {
            "shark": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "CLOSE", "evidence": "official shark rendered"},
            "background": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "CLOSE", "evidence": "official ocean composition"},
        },
        "density": {"screen": "/app", "viewport": "desktop_1366x768", "first_viewport_product": True, "nested_panel_depth": 1},
        "mobile": {"screen": "/app", "viewport": "mobile_390x844", "overflow": False},
        "runtime": {"js_errors": [], "broken_images": []},
        "journeys": [{"journey": "sports", "route": "/app", "expected": "/match/", "actual": "/match/m-1", "pass": True}],
    }


def test_acceptance_fixture_detects_all_demonstrated_failures():
    issues = detect_product_qa_issues(failing_observation(), detected_at="2026-08-30T10:00:00+02:00")
    categories = {item["category"] for item in issues}
    assert {"NAVIGATION", "SPORTS_TRUTH", "SPORTS_KNOWLEDGE", "SUMMARY_TRUTH", "MEDIA_RIGHTS", "CLIENT_COPY", "VISUAL_SHARK", "VISUAL_BACKGROUND", "UI_DENSITY", "MOBILE_LAYOUT", "JAVASCRIPT", "BROKEN_IMAGE", "USER_JOURNEY"} <= categories
    assert next(item for item in issues if item["category"] == "NAVIGATION")["severity"] == "P0"
    assert next(item for item in issues if item["category"] == "SPORTS_TRUTH")["severity"] == "P0"
    assert next(item for item in issues if item["category"] == "SPORTS_KNOWLEDGE")["worker"] == "sports_knowledge_qa"
    assert next(item for item in issues if item["category"] == "SUMMARY_TRUTH")["worker"] == "summary_truth_qa"
    assert next(item for item in issues if item["category"] == "MEDIA_RIGHTS")["worker"] == "media_rights_qa"


def test_clean_fixture_is_a_real_pass_candidate():
    assert detect_product_qa_issues(clean_observation()) == []


def test_memory_keeps_first_seen_and_recurrence(tmp_path: Path):
    first = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T10:00:00+02:00",
    )
    second = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-31T10:00:00+02:00",
    )
    first_by_id = {item["issue_id"]: item for item in first["issues"]}
    second_by_id = {item["issue_id"]: item for item in second["issues"]}
    assert first_by_id.keys() == second_by_id.keys()
    for issue_id in first_by_id:
        assert second_by_id[issue_id]["first_seen"] == first_by_id[issue_id]["first_seen"]
        assert second_by_id[issue_id]["seen_count"] == 2


def test_critical_scope_does_not_resolve_full_findings_or_replace_full_baseline(tmp_path: Path):
    failing = {**failing_observation(), "scope": "full", "run_id": "PQA-FULL-FAIL"}
    critical = {**clean_observation(), "scope": "critical", "run_id": "PQA-CRITICAL-PASS"}
    full_clean = {**clean_observation(), "scope": "full", "run_id": "PQA-FULL-PASS"}

    record_product_qa_run(failing, project_root=tmp_path, storage_root=tmp_path / "ce")
    critical_result = record_product_qa_run(critical, project_root=tmp_path, storage_root=tmp_path / "ce")
    status_after_critical = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")

    assert critical_result["result"] == "PASS"
    assert status_after_critical["open_issue_count"] > 0
    assert critical_result["previous_good_run_id"] is None
    assert critical_result["previous_good_critical_run_id"] == "PQA-CRITICAL-PASS"

    full_result = record_product_qa_run(full_clean, project_root=tmp_path, storage_root=tmp_path / "ce")
    assert full_result["result"] == "PASS"
    assert full_result["previous_good_run_id"] == "PQA-FULL-PASS"


def test_founder_override_and_calibration_are_honest(tmp_path: Path):
    record_product_qa_run(clean_observation(), project_root=tmp_path, storage_root=tmp_path / "ce")
    status = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")
    assert status["founder_overrides"][0]["type"] == "FOUNDER_QA_OVERRIDE"
    assert status["founder_overrides"][0]["previous_automation_result"] == "PASS"
    assert status["founder_overrides"][0]["founder_result"] == "FAIL"
    assert all(item["calibration"]["state"] == "INSUFFICIENT_HISTORY" for item in status["workers"])


def test_pause_resume_changes_only_product_qa_control(tmp_path: Path):
    paused = set_product_qa_pause(tmp_path, paused=True, actor="Founder", storage_root=tmp_path / "ce")
    assert paused["paused"] is True
    resumed = set_product_qa_pause(tmp_path, paused=False, actor="Founder", storage_root=tmp_path / "ce")
    assert resumed["paused"] is False
    assert len(resumed["history"]) == 2


def test_open_product_qa_issues_become_product_review_findings(tmp_path: Path):
    record_product_qa_run(failing_observation(), project_root=tmp_path, storage_root=tmp_path / "ce")
    status = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")
    findings = product_qa_review_findings(status)
    assert findings
    assert {item["priority"] for item in findings} >= {"P0", "P1"}
    assert all(item["automatic_execution_allowed"] is False for item in findings)


def test_sentinel_preserves_exact_product_qa_evidence_fields():
    raw = {
        "issue_id": "PQA-STABLE",
        "stable_key": "worker|navigation|/app|desktop|partidos",
        "title": "Topbar bloqueada",
        "category": "NAVIGATION",
        "severity": "critical",
        "worker": "digital_user_journey_tester",
        "screen": "/app",
        "viewport": "desktop_1366x768",
        "element": "Partidos",
        "expected": "/calendar",
        "actual": "/app",
        "evidence": "elementFromPoint no devuelve el enlace",
        "screenshot": "evidence/home.png",
        "production_sha": "abc123",
        "confidence": "HIGH",
    }
    first = normalize_sentinel_issue(raw, "autonomous_product_qa")
    second = normalize_sentinel_issue({**raw, "actual": "overlay intercepts click"}, "autonomous_product_qa")
    merged = upsert_sentinel_issues([first], [second])
    assert len(merged) == 1
    assert merged[0]["issue_id"] == "PQA-STABLE"
    assert merged[0]["seen_count"] == 2
    assert merged[0]["actual"] == "overlay intercepts click"
