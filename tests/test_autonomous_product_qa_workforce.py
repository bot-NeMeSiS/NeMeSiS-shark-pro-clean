from __future__ import annotations

from pathlib import Path

from engines.autonomous_product_qa_engine import (
    PINNED_REGRESSION_CONTRACTS,
    QA_EXECUTION_POLICY,
    build_quality_director_decision,
    build_autonomous_product_qa_status,
    detect_product_qa_issues,
    evaluate_production_sentinel,
    product_qa_review_findings,
    record_product_qa_run,
    set_product_qa_pause,
)
from engines.sentinel_issues_engine import (
    ISSUE_STATUSES,
    build_sentinel_issues_summary,
    canonicalize_sentinel_memory,
    normalize_sentinel_issue,
    reconcile_autonomous_workforce_evidence,
    upsert_sentinel_issues,
)
from engines.sentinel_codex_outbox_engine import write_codex_outbox
from engines.shark_sentinel_engine import _inspect_html, build_codex_prompts
from tools.run_autonomous_product_qa import _sports_priority_regression


def test_daily_policy_includes_sports_knowledge_summary_media_rights_and_time():
    checks = set(QA_EXECUTION_POLICY["daily"]["checks"])
    assert {"sports_knowledge", "summary_truth", "media_rights", "temporal_context"} <= checks


def test_sports_priority_regression_uses_canonical_ranking_without_external_calls(app_module):
    result = _sports_priority_regression(app_module)
    order = result["order"]
    assert result["status"] == "PASS"
    assert result["external_calls"] == 0
    for important in ("bayern-stuttgart", "lille-psg", "milan-venezia"):
        assert order.index(important) < order.index("k-league-2")
        assert order.index(important) < order.index("chinese-super-league")


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
        "temporal_context": {
            "screen": "match surfaces",
            "checked_cards": 9,
            "missing_cards": 2,
            "ambiguous_cards": 1,
            "cross_surface_consistent": False,
            "madrid_time": False,
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
            "shark": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MAJOR_GAP", "evidence": "legacy shark marker"},
            "background": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "REBUILD_REQUIRED", "evidence": "flat background"},
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
        "temporal_context": {"screen": "match surfaces", "checked_cards": 9, "missing_cards": 0, "ambiguous_cards": 0, "cross_surface_consistent": True, "madrid_time": True},
        "sports_knowledge": {"screen": "/match/m-1", "lineup_confirmed": True, "lineup_player_links": 1, "summary_ai_calls": 0, "summary_unsupported_claims": 0, "unsafe_media_visible": 0},
        "client_copy": {"screen": "/live", "visible_text": "No hay partidos en directo."},
        "visual": {
            "shark": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MINOR_GAP", "evidence": "official shark rendered"},
            "background": {"screen": "/app", "viewport": "desktop_1366x768", "classification": "MINOR_GAP", "evidence": "official ocean composition"},
        },
        "density": {"screen": "/app", "viewport": "desktop_1366x768", "first_viewport_product": True, "nested_panel_depth": 1},
        "mobile": {"screen": "/app", "viewport": "mobile_390x844", "overflow": False},
        "runtime": {"js_errors": [], "broken_images": []},
        "journeys": [{"journey": "sports", "route": "/app", "expected": "/match/", "actual": "/match/m-1", "pass": True}],
    }


def test_acceptance_fixture_detects_all_demonstrated_failures():
    issues = detect_product_qa_issues(failing_observation(), detected_at="2026-08-30T10:00:00+02:00")
    categories = {item["category"] for item in issues}
    assert {"NAVIGATION", "SPORTS_TRUTH", "TEMPORAL_CONTEXT", "SPORTS_KNOWLEDGE", "SUMMARY_TRUTH", "MEDIA_RIGHTS", "CLIENT_COPY", "VISUAL_SHARK", "VISUAL_BACKGROUND", "UI_DENSITY", "MOBILE_LAYOUT", "JAVASCRIPT", "BROKEN_IMAGE", "USER_JOURNEY"} <= categories
    assert next(item for item in issues if item["category"] == "NAVIGATION")["severity"] == "P0"
    assert next(item for item in issues if item["category"] == "SPORTS_TRUTH")["severity"] == "P0"
    assert next(item for item in issues if item["category"] == "SPORTS_TRUTH")["worker"] == "sports_truth_qa"
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


def test_two_full_clean_retests_resolve_non_visual_but_keep_founder_visual_review(tmp_path: Path):
    failing = {**failing_observation(), "scope": "full", "run_id": "PQA-FAIL"}
    clean_one = {**clean_observation(), "scope": "full", "run_id": "PQA-CLEAN-1"}
    clean_two = {**clean_observation(), "scope": "full", "run_id": "PQA-CLEAN-2"}

    record_product_qa_run(failing, project_root=tmp_path, storage_root=tmp_path / "ce")
    record_product_qa_run(clean_one, project_root=tmp_path, storage_root=tmp_path / "ce")
    record_product_qa_run(clean_two, project_root=tmp_path, storage_root=tmp_path / "ce")
    status = build_autonomous_product_qa_status(tmp_path, storage_root=tmp_path / "ce")
    by_category = {}
    for issue in status["issues"]:
        by_category.setdefault(issue["category"], []).append(issue)

    assert all(item["status"] == "RESOLVED" for item in by_category["NAVIGATION"])
    assert all(item["status"] == "RESOLVED" for item in by_category["SPORTS_TRUTH"])
    assert all(item["status"] == "RESOLVED" for item in by_category["CLIENT_COPY"])
    assert all(item["status"] == "FIXED_PENDING_VERIFICATION" for item in by_category["VISUAL_SHARK"])
    assert all(item["status"] == "FIXED_PENDING_VERIFICATION" for item in by_category["VISUAL_BACKGROUND"])


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


def test_canonical_ledger_rejects_synthetic_404_and_codex_noise():
    synthetic = normalize_sentinel_issue({
        "title": "Ruta devuelve Not Found",
        "route": "/ruta-inventada-v999",
        "evidence": "Probe de QA sin navegación interna real.",
        "actual": "404",
        "status": "OPEN",
    })
    context_only = normalize_sentinel_issue({
        "title": "Contexto sin muestra real",
        "area": "growth",
        "status": "INSUFFICIENT_EVIDENCE",
        "evidence": "No existe todavía muestra REAL_USER suficiente.",
    })
    memory = canonicalize_sentinel_memory({"issues": [synthetic, context_only], "events": []})
    summary = build_sentinel_issues_summary("TEST", memory)

    assert ISSUE_STATUSES == [
        "OPEN_REAL", "FIXED_PENDING_VERIFICATION", "RESOLVED", "FALSE_POSITIVE",
        "STALE", "DUPLICATE", "EXTERNAL_BLOCKER", "INSUFFICIENT_EVIDENCE",
    ]
    assert summary["counts"]["open"] == 0
    assert summary["issue_health"]["false_positive"] == 1
    assert summary["issue_health"]["insufficient_evidence"] == 1
    assert summary["codex_ready_issues"] == []


def test_founder_issue_gate_has_no_indefinite_pending_statuses(tmp_path: Path):
    summary = reconcile_autonomous_workforce_evidence(
        tmp_path,
        latest_product_qa={"result": "PASS", "evidence_complete": True, "issues_detected": 0},
        production_sha="sha-under-review",
        save=False,
    )
    by_key = {item.get("stable_key"): item for item in summary["issues"]}

    assert by_key["founder-shark-identity"]["status"] == "OPEN_REAL"
    assert by_key["founder-ocean-background"]["status"] == "OPEN_REAL"
    assert by_key["founder-reference-mismatch"]["status"] == "OPEN_REAL"
    assert by_key["founder-false-live-kpi"]["status"] == "RESOLVED"
    assert by_key["founder-rectangle-fatigue"]["status"] == "RESOLVED"
    assert not any(item["status"] == "FIXED_PENDING_VERIFICATION" for item in by_key.values())

def test_honest_empty_sports_state_is_not_an_issue_or_codex_work():
    context = " Consulta calendario, favoritos y próximos encuentros cuando haya datos reales."
    html = (
        "<html><body><main class='sports-screen'><section class='v933-empty-state'>"
        "<h1>Partidos</h1><p>No hay partidos en este momento.</p>"
        f"<p>{context * 5}</p></section></main></body></html>"
    )

    assert _inspect_html("FREE", "/partidos", 200, html) == []
    assert build_codex_prompts([]) == []


def test_codex_outbox_accepts_only_verified_open_real(tmp_path: Path):
    blocked = normalize_sentinel_issue({
        "title": "Contexto sin evidencia",
        "status": "INSUFFICIENT_EVIDENCE",
        "evidence": "Muestra real pendiente.",
    })
    ready = normalize_sentinel_issue({
        "title": "Enlace interno roto",
        "status": "OPEN_REAL",
        "route": "/app",
        "evidence": "Clic real desde Home termina en una ruta 404.",
        "actual": "404 después del clic",
        "expected": "Match Center",
        "evidence_origin": "LOCAL_QA",
        "evidence_sufficient": True,
    })
    result = write_codex_outbox(tmp_path, [blocked, ready])

    assert result["prompt_count"] == 1
    assert ready["id"] in Path(result["combined_path"]).read_text(encoding="utf-8")
    assert blocked["id"] not in Path(result["combined_path"]).read_text(encoding="utf-8")


def test_quality_director_never_lets_lower_evidence_override_founder_failure():
    founder_issue = {
        "issue_id": "FOUNDER-TOPBAR",
        "category": "NAVIGATION",
        "severity": "P0",
        "status": "OPEN_REAL",
        "evidence_origin": "FOUNDER_QA_OVERRIDE",
    }
    decision = build_quality_director_decision(
        [founder_issue],
        evidence_complete=True,
        regression_manager={"items": []},
        supplemental_evidence={"NAVIGATION": {"status": "PASS", "origin": "UNIT_STATIC_TEST"}},
    )

    assert decision["decision"] == "FAIL"
    assert decision["release_quality_pass"] is False
    assert decision["open_p0"] == 1
    assert next(item for item in decision["gates"] if item["area"] == "NAVIGATION")["authority"] == "FOUNDER_CONFIRMED_FAILURE"


def test_regression_manager_pins_all_known_founder_regressions(tmp_path: Path):
    result = record_product_qa_run(
        clean_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T11:00:00+02:00",
    )

    manager = result["regression_manager"]
    assert manager["protected_regressions"] == 17
    assert {item["regression_id"] for item in manager["items"]} == set(PINNED_REGRESSION_CONTRACTS)
    assert next(item for item in manager["items"] if item["regression_id"] == "OFFICIAL_SHARK_REFERENCE")["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert next(item for item in manager["items"] if item["regression_id"] == "OFFICIAL_BACKGROUND_REFERENCE")["status"] == "FOUNDER_REVIEW_REQUIRED"
    assert next(item for item in manager["items"] if item["regression_id"] == "VISUAL_FALSE_PASS_RECURRENCE")["status"] == "FOUNDER_REVIEW_REQUIRED"


def test_regression_manager_increments_recurrence_after_clean_retest(tmp_path: Path):
    record_product_qa_run(
        clean_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-30T11:00:00+02:00",
    )
    result = record_product_qa_run(
        failing_observation(),
        project_root=tmp_path,
        storage_root=tmp_path / "ce",
        now="2026-08-31T11:00:00+02:00",
    )

    topbar = next(item for item in result["regression_manager"]["items"] if item["regression_id"] == "TOPBAR_REAL_NAVIGATION")
    assert topbar["status"] == "FAIL"
    assert topbar["recurrence_count"] == 1
    assert result["quality_director"]["decision"] == "FAIL"


def test_production_sentinel_requires_all_post_deploy_checks():
    checks = {
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
    certified = evaluate_production_sentinel(
        {"production_sha": "sha-good", "deployment": checks},
        {"open_p0": 0},
    )
    incomplete = evaluate_production_sentinel(
        {"production_sha": "sha-unknown", "deployment": {**checks, "logs_recent": "NOT_AVAILABLE"}},
        {"open_p0": 0},
    )

    assert certified["result"] == "PRODUCTION_CERTIFIED"
    assert certified["rollback_recommended"] is False
    assert incomplete["result"] == "BLOCKED"


def test_production_sentinel_recommends_rollback_for_post_deploy_p0():
    decision = evaluate_production_sentinel(
        {
            "production_sha": "sha-bad",
            "deployment": {
                "health": "PASS",
                "sha_alignment": "PASS",
                "logs_recent": "PASS",
                "critical_routes": "PASS",
                "topbar_click_journey": "FAIL",
                "mobile_nav": "PASS",
                "sports_truth": "PASS",
                "temporal_context": "PASS",
                "performance_sample": "PASS",
                "critical_visual_surfaces": "PASS",
                "client_admin_protection": "PASS",
            },
        },
        {"open_p0": 1},
    )

    assert decision["result"] == "REGRESSION_DETECTED"
    assert decision["rollback_recommended"] is True
