"""Continuous SHARK Sentinel loop.

Safe permanent inspection layer. It coordinates route/user/profile diagnostics
using the existing SHARK Sentinel engine, compares against an internal baseline,
and returns prioritized issues/prompts without code writes, deploys, secrets,
DB deletion, payment mutation, Telegram sending, or fake data.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha1
import json
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

from engines.shark_sentinel_engine import (
    FORBIDDEN_AUTOMATIC_ACTIONS,
    PROFILES,
    build_codex_prompts,
    build_recommended_actions,
    build_static_sentinel_summary,
    run_static_flask_inspection,
    summarize_issues_by,
)
from engines.sentinel_improvement_workflow_engine import build_workflow_from_sentinel_result
from engines.visual_company_worker_engine import run_visual_company_worker


MADRID_TZ = ZoneInfo("Europe/Madrid")

CYCLES = {
    "quick": ["runtime", "admin protection", "master tick protection", "critical routes"],
    "client": ["visitor", "FREE", "PRO", "ELITE", "client navigation"],
    "admin": ["dashboard", "Company OS", "Company Audit", "Auto Improvement", "users", "payments"],
    "visual": ["visual markers", "bottom nav", "floating SHARK", "mojibake", "empty states"],
    "data": ["picks", "live", "fixtures", "odds", "safe states", "API guard"],
    "telegram": ["configuration", "dedupe", "no filler", "real-send honesty"],
    "improvement": ["priorities", "safe actions", "approval required", "Codex prompts"],
    "workflow": ["issue detection", "dedupe", "grouping", "tasks", "Codex prompts", "revalidation"],
    "visual-worker": ["visual worker", "routes", "tasks", "Codex prompts", "safe revalidation"],
    "company-worker": ["company worker", "client", "admin", "data", "revenue", "release"],
    "full-company-qa": ["full company QA", "visual", "product", "data", "admin", "workflow"],
    "full": ["quick", "client", "admin", "visual", "data", "telegram", "improvement"],
}

ISSUE_STATUSES = [
    "open",
    "acknowledged",
    "suggested",
    "safe_fixed",
    "needs_codex",
    "needs_admin_approval",
    "ignored",
    "resolved",
    "recurring",
]

ACTION_LEVELS = {
    "level_1_diagnostic": ["detectar", "reportar", "priorizar", "generar prompt"],
    "level_2_safe_internal_fix": ["limpiar cache propia", "marcar issue revisado", "regenerar reporte", "deduplicar incidencias", "recalcular score interno"],
    "level_3_approval_required": ["sync datos", "Telegram test", "archivar picks", "tocar membresías", "preparar release", "ejecutar prompt Codex", "cambios visuales/templates/CSS", "cambios DB real"],
    "level_4_forbidden_automatic": FORBIDDEN_AUTOMATIC_ACTIONS,
}

V864_VISUAL_RULES = [
    "cards_gigantes_o_pobres",
    "posible_overflow_horizontal",
    "bottom_nav_duplicada",
    "floating_shark_duplicado",
    "admin_con_navegacion_cliente",
    "section_headers_ausentes",
    "empty_states_pobres",
    "mojibake_visible",
    "cta_principal_ausente",
    "cards_sin_jerarquia",
    "mobile_safe_area_debil",
    "pc_sin_densidad_dashboard",
]

V878_LAYER_PURGE_RULES = [
    "deprecated_visual_classes_in_primary_templates",
    "duplicate_button_labels",
    "duplicate_cta_per_card",
    "client_nav_inside_admin",
    "admin_nav_inside_client",
    "floating_shark_duplicate",
    "macro_label_duplicate",
    "too_many_actions_per_card",
    "oversized_empty_states",
    "mobile_overflow_risk",
    "stripe_operativo_false_claim",
    "telegram_filler_copy",
    "openai_false_active_claim",
    "broken_logo_without_fallback",
]

V879_FINAL_PRODUCT_RULES = [
    "duplicated_visible_cta_labels",
    "oversized_black_empty_space",
    "giant_cards_without_hierarchy",
    "client_admin_navigation_mixed",
    "floating_shark_over_navigation",
    "technical_endpoint_visible_as_main_content",
    "english_technical_copy_in_client",
    "none_null_undefined_visible",
    "mojibake_visible",
    "unsafe_payment_operational_claim",
    "unsafe_openai_operational_claim",
    "telegram_filler_or_fake_send_claim",
    "more_than_two_actions_per_card",
    "missing_safe_state_for_real_data_absence",
]

V880_PROBLEM_SWEEP_RULES = [
    "render_local_version_mismatch",
    "runtime_last_error_active",
    "configured_api_without_visible_data_state",
    "matches_empty_without_safe_explanation",
    "live_empty_without_safe_explanation",
    "picks_without_odds_or_selection_state",
    "logo_cache_zero_without_fallback",
    "admin_api_unprotected",
    "cron_unprotected",
    "traceback_or_debug_visible",
    "workspace_release_contains_forbidden_files",
    "old_checks_reject_current_version",
    "sentinel_score_high_with_real_problem",
]

V881_NAV_DUPLICATION_RULES = [
    "duplicate_sidebar_container",
    "duplicate_nav_href_in_same_zone",
    "duplicate_nav_label_in_same_zone",
    "client_nav_visible_in_admin",
    "admin_nav_visible_in_client",
    "bottom_nav_visible_in_admin",
    "floating_shark_visible_in_admin",
    "command_strip_duplicate",
    "legacy_client_rail_rendered",
    "duplicated_label_picks_picks",
    "duplicated_label_shark_shark",
    "duplicated_label_telegram_telegram",
]

V882_CORE_PRODUCT_RULES = [
    "sports_screen_empty_without_safe_explanation",
    "matches_empty_without_sync_context",
    "live_empty_without_provider_context",
    "picks_empty_without_review_state",
    "api_configured_cache_zero_without_admin_task",
    "filters_hide_all_without_reset_cta",
    "logo_cache_zero_without_fallback",
    "sentinel_score_high_with_core_product_gap",
]

V883_VISUAL_COMPANY_WORKER_RULES = [
    "visual_worker_detects_duplicate_cta",
    "visual_worker_detects_mojibake",
    "visual_worker_detects_none_null_undefined_visible",
    "visual_worker_detects_client_nav_in_admin",
    "visual_worker_detects_admin_nav_in_client",
    "visual_worker_detects_sports_empty_without_safe_state",
    "visual_worker_detects_render_version_mismatch",
    "visual_worker_creates_grouped_issues",
    "visual_worker_creates_tasks",
    "visual_worker_creates_codex_prompts",
    "visual_worker_never_auto_codes",
    "visual_worker_never_auto_deploys",
]

V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_RULES = [
    "client_buttons_need_real_destination",
    "admin_buttons_need_operational_destination",
    "empty_href_or_hash_href_detected",
    "javascript_href_detected",
    "client_admin_navigation_crossing_detected",
    "duplicate_cta_labels_detected",
    "sports_screens_need_rows_or_safe_state",
    "picks_need_pending_odds_or_review_state",
    "shark_safe_mode_must_be_visible_when_openai_missing",
    "payments_must_not_claim_operational_without_stripe",
    "telegram_must_not_claim_fake_sends",
    "admin_apis_and_cron_must_stay_protected",
]

V885_CLIENT_SIDEBAR_RESTORE_RULES = [
    "client_desktop_requires_single_sidebar",
    "client_mobile_requires_single_bottom_nav",
    "admin_must_not_render_client_sidebar",
    "admin_must_not_render_client_bottom_nav",
    "admin_must_not_render_client_floating_shark",
    "client_must_not_render_admin_rail",
    "client_sidebar_links_must_be_real",
    "client_sidebar_must_mark_active_route",
    "no_duplicate_sidebar_labels",
    "no_hash_or_javascript_nav_links",
]

V888_REAL_ERRORS_SWEEP_RULES = [
    "render_local_version_mismatch_must_be_reported",
    "telegram_cron_nameerror_or_internal_error_must_fail",
    "queue_skipped_state_must_be_defined",
    "matches_need_real_data_or_safe_empty_state",
    "live_needs_real_score_minute_or_safe_pending_state",
    "picks_need_odds_selection_or_review_state",
    "client_admin_navigation_must_stay_isolated",
    "mobile_must_not_have_horizontal_overflow",
    "openai_missing_must_show_safe_mode",
    "stripe_missing_must_not_show_operational",
    "logo_cache_zero_requires_fallback",
    "mojibake_none_null_undefined_visible_are_issues",
    "favicon_must_not_404",
    "sentinel_score_must_reflect_real_blockers",
]

V888_SENTINEL_AUTOPILOT_RULES = [
    "autopilot_converts_sentinel_issues_to_tasks",
    "autopilot_converts_visual_worker_findings_to_tasks",
    "autopilot_generates_codex_prompts",
    "autopilot_prioritizes_critical_high_medium_low",
    "autopilot_keeps_memory_without_secrets",
    "autopilot_requires_approval_for_code_routes_db_payments_telegram_deploy",
    "autopilot_never_auto_deploys",
    "autopilot_never_auto_pushes",
    "autopilot_never_sends_real_telegram",
    "autopilot_never_invents_sports_data",
]

V889_TELEGRAM_PREMIUM_PICK_RULES = [
    "telegram_pick_requires_real_match",
    "telegram_pick_requires_real_odds",
    "telegram_pick_requires_clear_selection",
    "telegram_pick_requires_quality_score",
    "telegram_pick_below_threshold_must_not_send",
    "telegram_pick_duplicate_must_skip",
    "telegram_pick_low_league_must_skip",
    "telegram_membership_variants_must_not_invent_extra_data",
    "telegram_pick_preview_api_must_be_admin_protected",
    "telegram_pick_dry_run_must_not_send_or_queue",
    "telegram_combi_requires_all_legs_with_real_odds",
    "telegram_result_tracking_must_not_invent_settlement",
    "telegram_visual_card_must_have_text_fallback",
    "telegram_no_filler_policy_must_win_over_empty_send",
]

V925_REFERENCE_PRODUCT_RULES = [
    "single_public_hero",
    "no_excessive_top_empty_space",
    "compact_cards_with_separated_values",
    "admin_client_navigation_isolated",
    "visible_copy_without_mojibake",
    "premium_safe_empty_states",
    "client_routes_never_500",
    "sports_routes_cache_first",
    "browser_qa_requires_real_screenshots",
    "sports_data_requires_source_and_real_values",
]

V926_DESKTOP_REFERENCE_RULES = [
    "desktop_no_empty_top_area",
    "desktop_hero_compact_above_fold",
    "desktop_two_or_three_column_layout",
    "admin_command_center_dense_and_separated",
    "client_desktop_dashboard_uses_wide_canvas",
    "sports_filters_and_data_above_fold",
    "desktop_cards_not_oversized",
    "admin_client_navigation_isolated",
    "sports_values_require_real_source",
    "browser_qa_desktop_requires_real_screenshots",
]

PC_DESKTOP_REFERENCE_RULES_V927 = [
    "important_content_must_start_in_first_desktop_viewport",
    "desktop_top_empty_space_must_stay_below_known_guard",
    "primary_cards_need_label_value_hint_and_action_when_applicable",
    "admin_needs_kpis_operations_next_action_and_compact_tables",
    "client_needs_dashboard_quick_actions_sports_state_and_next_action",
    "sports_needs_filters_provider_state_and_safe_empty_state_above_fold",
    "critical_actions_must_not_be_hidden_below_dead_space",
    "admin_and_client_navigation_must_remain_isolated",
    "sports_values_require_real_source_or_explicit_safe_state",
    "desktop_pixel_perfect_requires_real_browser_screenshots",
]

V928_CANONICAL_REFERENCE_RULES = [
    "canonical_shell_per_role",
    "admin_client_navigation_isolated",
    "client_desktop_and_mobile_are_distinct",
    "real_data_or_safe_state_only",
    "single_public_hero",
    "responsive_overflow_guard",
    "browser_evidence_required_for_visual_claims",
    "pixel_perfect_requires_human_reference_review",
]


def _v928_browser_evidence() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "data" / "runtime" / "autonomous_company_sentinel" / "browser_qa_status.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        payload = {}
    captured = int(payload.get("screenshots_captured") or 0)
    return {"status": "screenshots_available" if captured else "browser_qa_required", "screenshots_captured": captured}


def build_v925_visual_product_snapshot(client: Any) -> dict[str, Any]:
    """Run safe visible-product checks without mutating data or requiring a browser."""
    routes = ["/", "/calendar", "/live", "/picks", "/shark"]
    route_status = {}
    rendered = {}
    for route in routes:
        try:
            response = client.get(route, follow_redirects=False)
            route_status[route] = int(response.status_code)
            rendered[route] = response.get_data(as_text=True) if response.status_code == 200 else ""
        except Exception:
            route_status[route] = 0
            rendered[route] = ""
    home_html = rendered.get("/") or ""
    visible_copy = " ".join(rendered.values()).lower()
    broken_tokens = [token for token in ("ãƒ", "â€", "â€”", "none</", "undefined</") if token in visible_copy]
    sports_safe_state = all(
        route_status.get(route, 0) < 500
        and any(marker in (rendered.get(route) or "").lower() for marker in ("sin ", "datos reales", "modo seguro", "proveedor"))
        for route in ("/calendar", "/live", "/picks")
    )
    return {
        "rules": V925_REFERENCE_PRODUCT_RULES,
        "route_status": route_status,
        "client_routes_no_500": all(status and status < 500 for status in route_status.values()),
        "single_public_hero": sum(
            bool({"v925-public-hero", "v928-home-hero"} & set(value.split()))
            for value in re.findall(r'class="([^"]*)"', home_html)
        ) == 1,
        "visible_mojibake_tokens": broken_tokens,
        "visible_copy_clean": not broken_tokens,
        "sports_safe_states_present": sports_safe_state,
        "browser_qa_status": _v928_browser_evidence()["status"],
        "pixel_perfect_claim_allowed": False,
        "no_mutations": True,
    }


def build_v926_desktop_snapshot(client: Any) -> dict[str, Any]:
    """Check V926 desktop contracts without mutating state or claiming browser evidence."""
    routes = ["/", "/app", "/calendar", "/live", "/picks", "/shark", "/telegram"]
    route_status: dict[str, int] = {}
    rendered: dict[str, str] = {}
    for route in routes:
        try:
            response = client.get(route, follow_redirects=False)
            route_status[route] = int(response.status_code)
            rendered[route] = response.get_data(as_text=True) if response.status_code == 200 else ""
        except Exception:
            route_status[route] = 0
            rendered[route] = ""
    combined = " ".join(rendered.values())
    return {
        "rules": V926_DESKTOP_REFERENCE_RULES,
        "route_status": route_status,
        "client_routes_no_500": all(status and status < 500 for status in route_status.values()),
        "home_desktop_marker": 'data-v926-template="home-public"' in rendered.get("/", "") or 'data-v928-template="home"' in rendered.get("/", ""),
        "calendar_board_marker": "v926-desktop-sports-board" in rendered.get("/calendar", "") or "v928-sports-board" in rendered.get("/calendar", ""),
        "live_board_marker": "v926-desktop-live-board" in rendered.get("/live", "") or "v928-live-board" in rendered.get("/live", ""),
        "picks_board_marker": "v926-desktop-picks-board" in rendered.get("/picks", "") or "v928-picks-board" in rendered.get("/picks", ""),
        "desktop_contract_markers_present": all(
            any(candidate in combined for candidate in alternatives)
            for alternatives in (("v926-desktop-shell", "v928-page"), ("v926-desktop-data-table", "v928-table-shell", "v928-safe-state"), ("v926-desktop-sports-board", "v928-sports-board"))
        ),
        "browser_qa_status": _v928_browser_evidence()["status"],
        "pixel_perfect_claim_allowed": False,
        "no_mutations": True,
        "no_external_calls": True,
        "no_fake_data": True,
    }


def build_v927_pc_desktop_snapshot(client: Any) -> dict[str, Any]:
    """Check V927 PC contracts without external calls or visual overclaims."""
    routes = ["/", "/app", "/calendar", "/live", "/picks", "/shark", "/telegram"]
    route_status: dict[str, int] = {}
    rendered: dict[str, str] = {}
    for route in routes:
        try:
            response = client.get(route, follow_redirects=False)
            route_status[route] = int(response.status_code)
            rendered[route] = response.get_data(as_text=True) if response.status_code == 200 else ""
        except Exception:
            route_status[route] = 0
            rendered[route] = ""
    combined = " ".join(rendered.values())
    return {
        "rules": PC_DESKTOP_REFERENCE_RULES_V927,
        "route_status": route_status,
        "client_routes_no_500": all(status and status < 500 for status in route_status.values()),
        "single_public_hero": sum(
            bool({"v925-public-hero", "v928-home-hero"} & set(value.split()))
            for value in re.findall(r'class="([^"]*)"', rendered.get("/", ""))
        ) == 1,
        "home_pc_marker": 'data-v927-template="home-public"' in rendered.get("/", "") or 'data-v928-template="home"' in rendered.get("/", ""),
        "calendar_toolbar_marker": "v927-data-toolbar" in rendered.get("/calendar", "") or "v928-filter-form" in rendered.get("/calendar", ""),
        "live_toolbar_marker": "v927-data-toolbar" in rendered.get("/live", "") or "v928-filter-tabs" in rendered.get("/live", ""),
        "picks_table_marker": "v927-table-card" in rendered.get("/picks", "") or "v928-picks-board" in rendered.get("/picks", ""),
        "desktop_contract_markers_present": all(
            any(candidate in combined for candidate in alternatives)
            for alternatives in (("v927-desktop-shell", "v928-page"), ("v927-status-strip", "v928-kpi-grid"), ("v927-client-hero-row", "v928-page-header"))
        ),
        "browser_qa_status": _v928_browser_evidence()["status"],
        "pixel_perfect_claim_allowed": False,
        "no_mutations": True,
        "no_external_calls": True,
        "no_fake_data": True,
    }


def build_v928_canonical_snapshot(client: Any) -> dict[str, Any]:
    """Report the active V928 contracts without mutating data or calling providers."""
    root = Path(__file__).resolve().parents[1]
    template_names = ["home.html", "client_app_center.html", "calendar.html", "live.html", "picks.html", "admin_dashboard.html"]
    template_text = "\n".join((root / "templates" / name).read_text(encoding="utf-8-sig", errors="replace") for name in template_names)
    css = (root / "static" / "v928-canonical.css").read_text(encoding="utf-8-sig", errors="replace")
    evidence = _v928_browser_evidence()
    route_status = {}
    for route in ("/", "/calendar", "/live", "/picks", "/api/runtime-version"):
        try:
            route_status[route] = int(client.get(route, follow_redirects=False).status_code)
        except Exception:
            route_status[route] = 0
    return {
        "rules": V928_CANONICAL_REFERENCE_RULES,
        "route_status": route_status,
        "routes_no_500": all(status and status < 500 for status in route_status.values()),
        "canonical_template_markers_present": all(marker in template_text for marker in ('data-v928-template="home"', 'data-v928-template="client_app_center"', 'data-v928-template="calendar"', 'data-v928-template="live"', 'data-v928-template="picks"', 'data-v928-template="admin_dashboard"')),
        "canonical_css_present": "V928 canonical reference system" in css,
        "browser_qa_status": evidence["status"],
        "screenshots_captured": evidence["screenshots_captured"],
        "pixel_perfect_claim_allowed": False,
        "no_mutations": True,
        "no_external_calls": True,
        "no_fake_data": True,
    }


def madrid_now() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def make_run_id(mode: str) -> str:
    raw = f"{mode}:{madrid_now()}"
    return "CSL-" + sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def _normalize_mode(mode: str | None) -> str:
    mode = (mode or "quick").strip().lower()
    if mode == "diagnostic":
        return "quick"
    if mode not in CYCLES:
        return "quick"
    return mode


def _decorate_issue(issue: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "issue_id": issue.get("id") or "ISSUE",
        "run_id": run_id,
        "timestamp_madrid": issue.get("timestamp_madrid") or madrid_now(),
        "profile": issue.get("profile") or "UNKNOWN",
        "route": issue.get("route") or "",
        "screen_area": issue.get("route") or "",
        "category": issue.get("category") or "unknown",
        "severity": issue.get("severity") or "info",
        "title": issue.get("title") or "Incidencia detectada",
        "description": issue.get("description") or "",
        "evidence": issue.get("evidence") or "",
        "expected_behavior": issue.get("expected_behavior") or "",
        "actual_behavior": issue.get("actual_behavior") or "",
        "suggested_fix": issue.get("suggested_fix") or "",
        "safe_auto_fix_possible": bool(issue.get("safe_auto_fix_possible")),
        "approval_required": bool(issue.get("requires_admin_approval")),
        "codex_prompt": issue.get("codex_prompt_suggestion") or "",
        "status": "open",
        "first_seen": issue.get("timestamp_madrid") or madrid_now(),
        "last_seen": madrid_now(),
        "occurrence_count": 1,
    }


def build_continuous_sentinel_summary(version: str = "") -> dict[str, Any]:
    base = build_static_sentinel_summary(version)
    return {
        "version": version,
        "sentinel_status": "continuous_loop_ready",
        "last_cycle": None,
        "global_score": None,
        "cycles": CYCLES,
        "profiles": list(PROFILES.keys()),
        "issues_open": 0,
        "issues_critical": 0,
        "issues_recurring": 0,
        "issues_by_category": {},
        "issues_by_profile": {},
        "routes_expected": sum(len(routes) for routes in PROFILES.values()),
        "safe_actions": ACTION_LEVELS["level_2_safe_internal_fix"],
        "approval_required_actions": ACTION_LEVELS["level_3_approval_required"],
        "forbidden_automatic_actions": ACTION_LEVELS["level_4_forbidden_automatic"],
        "codex_prompts": base["codex_prompt_suggestions"],
        "next_focus": ["Ejecutar quick cycle", "Revisar issues high/critical", "Usar prompts Codex con aprobación"],
        "history_recent": [],
        "browser_note": "browser visual QA not available locally unless Playwright is installed and run explicitly",
        "visual_rules_v864": V864_VISUAL_RULES,
        "visual_rules_v878": V878_LAYER_PURGE_RULES,
        "visual_rules_v879": V879_FINAL_PRODUCT_RULES,
        "problem_sweep_rules_v880": V880_PROBLEM_SWEEP_RULES,
        "nav_duplication_rules_v881": V881_NAV_DUPLICATION_RULES,
        "core_product_rules_v882": V882_CORE_PRODUCT_RULES,
        "visual_company_worker_rules_v883": V883_VISUAL_COMPANY_WORKER_RULES,
        "client_admin_functional_flow_rules_v884": V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_RULES,
        "client_sidebar_restore_rules_v885": V885_CLIENT_SIDEBAR_RESTORE_RULES,
        "real_errors_sweep_rules_v888": V888_REAL_ERRORS_SWEEP_RULES,
        "sentinel_autopilot_rules_v888": V888_SENTINEL_AUTOPILOT_RULES,
        "telegram_premium_pick_rules_v889": V889_TELEGRAM_PREMIUM_PICK_RULES,
        "reference_product_rules_v925": V925_REFERENCE_PRODUCT_RULES,
        "desktop_reference_rules_v926": V926_DESKTOP_REFERENCE_RULES,
        "pc_desktop_reference_rules_v927": PC_DESKTOP_REFERENCE_RULES_V927,
        "sentinel_autopilot_ready": True,
        "visual_company_worker_ready": True,
        "visual_big_leap_ready": True,
        "improvement_workflow_ready": True,
        "workflow_cycle": "Detectar -> Priorizar -> Proponer -> Aplicar con Codex/Admin -> Revalidar -> Resolver",
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }


def run_continuous_sentinel_cycle(client: Any, version: str = "", mode: str = "quick", dry_run: bool = True) -> dict[str, Any]:
    mode = _normalize_mode(mode)
    run_id = make_run_id(mode)
    static_result = run_static_flask_inspection(client, version)
    v925_visual_snapshot = build_v925_visual_product_snapshot(client)
    v926_desktop_snapshot = build_v926_desktop_snapshot(client)
    v927_pc_desktop_snapshot = build_v927_pc_desktop_snapshot(client)
    v928_canonical_snapshot = build_v928_canonical_snapshot(client)
    static_issues = static_result.get("issues", [])
    safe_data_notes = [
        issue
        for issue in static_issues
        if issue.get("category") == "data_reality"
        and issue.get("severity") == "low"
        and "estado seguro" in f"{issue.get('description', '')} {issue.get('actual_behavior', '')}".lower()
    ]
    actionable_static_issues = [issue for issue in static_issues if issue not in safe_data_notes]
    issues = [_decorate_issue(issue, run_id) for issue in actionable_static_issues]
    visual_worker_result = {}
    if mode in {"visual-worker", "company-worker", "full-company-qa"}:
        worker_mode = "full" if mode in {"company-worker", "full-company-qa"} else "visual"
        visual_worker_result = run_visual_company_worker(client, version, mode=worker_mode, dry_run=dry_run)
        issues.extend(_decorate_issue(issue, run_id) for issue in visual_worker_result.get("issues", []))
    by_severity = summarize_issues_by(issues, "severity")
    by_category = summarize_issues_by(issues, "category")
    by_profile = summarize_issues_by(issues, "profile")
    high_or_critical = sum(1 for issue in issues if issue["severity"] in {"critical", "high"})
    score = max(0, round(10 - high_or_critical * 1.5 - len(issues) * 0.05, 1))
    result = {
        "run_id": run_id,
        "timestamp_madrid": madrid_now(),
        "version": version,
        "mode": mode,
        "dry_run": bool(dry_run),
        "status": "completed_diagnostic_only",
        "score": score,
        "routes_checked": static_result.get("routes_reviewed", 0),
        "profiles_checked": static_result.get("profiles", []),
        "issues": issues,
        "warnings": [
            "No browser real ejecutado en modo static.",
            "No se ejecutan acciones peligrosas.",
            "Los hallazgos de texto técnico son candidatos a revisar, no datos inventados.",
            "Las pantallas deportivas sin filas reales pero con estado seguro se tratan como aviso operativo, no incidencia.",
            "Reglas visuales V864 revisadas por marcadores estáticos; browser QA es opcional.",
            "Reglas V878 de purga visual revisadas por contrato ns-* y marcadores deprecated.",
            "Reglas V879 finales revisan producto visible, CTAs, espacios, copy y estados seguros.",
            "Reglas V880 revisan problemas reales de deploy, datos, rutas, protección y release.",
            "Reglas V881 revisan duplicación real de navegación, rail, bottom nav, dock y floating SHARK.",
            "Reglas V882 revisan núcleo deportivo: partidos, directo, picks, sync, cache y estados seguros.",
            "Reglas V883 integran Visual Company Worker: issues, tasks, prompts y revalidacion sin auto-code ni auto-deploy.",
        ],
        "issues_by_severity": by_severity,
        "issues_by_category": by_category,
        "issues_by_profile": by_profile,
        "issues_open": len(issues),
        "issues_critical": by_severity.get("critical", 0),
        "issues_recurring": 0,
        "safe_actions": ACTION_LEVELS["level_2_safe_internal_fix"],
        "approval_required_actions": ACTION_LEVELS["level_3_approval_required"],
        "forbidden_automatic_actions": ACTION_LEVELS["level_4_forbidden_automatic"],
        "codex_prompts": build_codex_prompts(actionable_static_issues),
        "recommended_actions": build_recommended_actions(actionable_static_issues),
        "safe_data_reality_notes": [
            {
                "route": issue.get("route"),
                "profile": issue.get("profile"),
                "title": issue.get("title"),
                "state": "Estado seguro presente; requiere proveedor/cache para filas reales.",
            }
            for issue in safe_data_notes
        ],
        "next_focus": ["Resolver high/critical primero", "Deduplicar issues recurrentes", "Preparar prompt Codex solo con aprobación"],
        "comparison": {
            "against_expected_baseline": "routes/profiles/status/safety checked",
            "against_last_cycle": "no persisted previous cycle in this safe local run",
            "against_visual_reference_internal": "V864 visual rules checked by static markers only",
            "against_commercial_rules": "no fake data and no irresponsible betting claims checked",
        },
        "visual_rules_v864": V864_VISUAL_RULES,
        "visual_rules_v878": V878_LAYER_PURGE_RULES,
        "visual_rules_v879": V879_FINAL_PRODUCT_RULES,
        "problem_sweep_rules_v880": V880_PROBLEM_SWEEP_RULES,
        "nav_duplication_rules_v881": V881_NAV_DUPLICATION_RULES,
        "core_product_rules_v882": V882_CORE_PRODUCT_RULES,
        "visual_company_worker_rules_v883": V883_VISUAL_COMPANY_WORKER_RULES,
        "real_errors_sweep_rules_v888": V888_REAL_ERRORS_SWEEP_RULES,
        "sentinel_autopilot_rules_v888": V888_SENTINEL_AUTOPILOT_RULES,
        "telegram_premium_pick_rules_v889": V889_TELEGRAM_PREMIUM_PICK_RULES,
        "reference_product_rules_v925": V925_REFERENCE_PRODUCT_RULES,
        "v925_visual_product_snapshot": v925_visual_snapshot,
        "desktop_reference_rules_v926": V926_DESKTOP_REFERENCE_RULES,
        "v926_desktop_snapshot": v926_desktop_snapshot,
        "pc_desktop_reference_rules_v927": PC_DESKTOP_REFERENCE_RULES_V927,
        "v927_pc_desktop_snapshot": v927_pc_desktop_snapshot,
        "canonical_reference_rules_v928": V928_CANONICAL_REFERENCE_RULES,
        "v928_canonical_snapshot": v928_canonical_snapshot,
        "sentinel_autopilot_ready": True,
        "visual_company_worker_v883": visual_worker_result,
        "visual_company_worker_ready": True,
        "visual_big_leap_ready": True,
        "improvement_workflow_ready": True,
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }
    if mode in {"workflow", "visual-worker", "company-worker", "full-company-qa"}:
        result["workflow"] = build_workflow_from_sentinel_result(result, version)
        if visual_worker_result:
            result["worker_tasks"] = visual_worker_result.get("suggested_tasks", [])
            result["worker_codex_prompts"] = visual_worker_result.get("codex_prompts", [])
    return result
