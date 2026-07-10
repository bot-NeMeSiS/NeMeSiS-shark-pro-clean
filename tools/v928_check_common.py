from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL"
V929_VERSION = "V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL"
ALLOWED_CONTAINER_VERSIONS = {VERSION, V929_VERSION}
FORBIDDEN_RELEASE_NAMES = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output"}


def read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def add(checks: list[dict], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def release_cleanliness(checks: list[dict]) -> None:
    current = read("VERSION.txt").strip().lstrip("\ufeff")
    deploy_name = "V929_DEPLOY_ROOT_CONTENTS" if current == V929_VERSION else "V928_DEPLOY_ROOT_CONTENTS"
    deploy = ROOT / "release_output" / deploy_name
    if not deploy.exists():
        add(checks, "deploy_root_pending_build", True, "will be audited after build")
        return
    forbidden = []
    for path in deploy.rglob("*"):
        rel = path.relative_to(deploy)
        if any(part in FORBIDDEN_RELEASE_NAMES for part in rel.parts) or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".zip", ".log"}:
            forbidden.append(str(rel))
    add(checks, "deploy_root_forbidden_count_zero", not forbidden, ", ".join(forbidden[:8]))


def base_checks() -> list[dict]:
    checks: list[dict] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes() if (ROOT / "VERSION.txt").exists() else b""
    current_version = version_bytes.decode("utf-8", errors="replace").strip().lstrip("\ufeff")
    add(checks, "version_v928_or_successor", current_version in ALLOWED_CONTAINER_VERSIONS)
    add(checks, "version_without_bom", not version_bytes.startswith(b"\xef\xbb\xbf"))
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/v928-canonical.css")
    add(checks, "app_version_matches", f"APP_VERSION = '{current_version}'" in app)
    add(checks, "canonical_css_loaded", "filename='v928-canonical.css'" in base and "?v={{ app_version }}" in base)
    cache_tag = "NEMESIS_CACHE_V929" if current_version == V929_VERSION else "NEMESIS_CACHE_V928"
    add(checks, "service_worker_current", cache_tag in app and "cache:'no-store'" in app and "cache:'reload'" in app)
    add(checks, "render_cache_only", "page_render_cache_only" in app and 'v928_page_render_external_calls\": False' in app)
    add(checks, "role_shell", "data-v928-shell=\"true\"" in base)
    add(checks, "no_pixel_perfect_claim", "v928_pixel_perfect_claim_allowed\": True" not in app)
    add(checks, "canonical_css_present", len(css) > 10000)
    return checks


def run(kind: str) -> dict:
    checks = base_checks()
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/v928-canonical.css")
    navigation = read("templates/components/v928_navigation.html")
    components = read("templates/components/v928_ui.html")
    if kind == "canonical":
        for flag in ["has_v928_canonical_reference_rebuild", "has_v928_admin_reference_rebuild", "has_v928_client_desktop_reference_rebuild", "has_v928_client_mobile_reference_rebuild", "has_v928_component_library", "has_v928_real_data_ui_guard", "has_v928_responsive_overflow_guard", "has_v928_reference_workers", "has_v928_browser_qa_pipeline"]:
            add(checks, flag, flag in app)
        add(checks, "reference_images_16", len(list((ROOT / "reference_images").rglob("*.png"))) == 16)
        add(checks, "single_role_shell_logic", "{% if show_admin_nav %}" in base and "{% elif is_client_area %}" in base and "{% elif not is_admin_surface %}" in base)
    elif kind == "admin":
        required = ["admin_dashboard.html", "admin_telegram_command_center.html", "admin_payments.html", "admin_memberships.html", "admin_users.html", "admin_picks.html", "admin_matches_sync.html", "admin_data_center.html", "admin_data_marketplace.html", "admin_automation_center.html", "admin_final_certification.html", "admin_real_launch.html"]
        for name in required:
            add(checks, f"admin_marker_{name}", "data-v928-template" in read(f"templates/{name}"))
        admin_sidebar = navigation.split("macro admin_sidebar", 1)[1].split("endmacro", 1)[0]
        add(
            checks,
            "admin_sidebar_separate",
            "data-nav-zone=\"admin-sidebar\"" in admin_sidebar
            and "'/app'" not in admin_sidebar
            and 'href="/app"' not in admin_sidebar,
        )
    elif kind == "client_desktop":
        required = ["home.html", "client_app_center.html", "calendar.html", "live.html", "picks.html", "match_detail.html", "track_record.html", "membership.html", "profile.html", "telegram.html", "shark.html"]
        for name in required:
            add(checks, f"client_marker_{name}", "data-v928-template" in read(f"templates/{name}"))
        add(checks, "client_desktop_nav", all(route in navigation for route in ["/app", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/profile"]))
    elif kind == "client_mobile":
        add(checks, "mobile_header", "v928-mobile-header" in navigation)
        add(checks, "mobile_bottom_nav", "v928-mobile-bottom-nav" in navigation and "repeat(5" in css)
        add(checks, "desktop_nav_hidden_mobile", ".v928-public-topbar, .v928-client-topbar, .v928-admin-topbar { display: none; }" in css)
        for width in [430, 820, 980]:
            add(checks, f"breakpoint_{width}", f"max-width: {width}px" in css)
    elif kind == "components":
        required = ["kpi_card", "status_chip", "status_card", "quick_action", "match_card", "live_card", "pick_card", "odds_block", "shark_confidence", "result_row", "provider_status", "data_table", "table_shell", "empty_state", "error_state", "safe_data_state", "plan_card", "profile_card", "admin_command_card", "activity_table", "worker_card"]
        for macro in required:
            add(checks, f"macro_{macro}", f"macro {macro}" in components)
        add(checks, "navigation_components", all(f"macro {name}" in navigation for name in ["public_topbar", "client_topbar", "admin_sidebar", "admin_topbar", "mobile_bottom_nav"]))
    elif kind == "real_data":
        targets = "\n".join(read(f"templates/{name}") for name in ["home.html", "admin_dashboard.html", "admin_telegram_command_center.html", "admin_automation_center.html", "admin_picks.html", "track_record.html", "picks.html", "live.html", "calendar.html"])
        for token in ["Arsenal vs Chelsea", "48.732", "125.684", "€18.732", "Real Madrid vs Borussia Dortmund"]:
            add(checks, f"no_demo_{token}", token.lower() not in targets.lower())
        add(checks, "publish_gate", "blocked_incomplete_pick" in app and "cuota real válida" in app)
        add(checks, "no_fake_roi_chart", "v793-chart-fake" not in read("templates/track_record.html"))
        add(checks, "match_form_payload_not_dumped", "{{ detail.get('home_form') or" not in read("templates/match_detail.html"))
        add(checks, "safe_odds_average", "stats.get('avg_odds')" not in read("templates/picks.html"))
        add(checks, "membership_cadence_not_duplicated", "'/mes' not in price_label|lower" in read("templates/membership.html"))
    elif kind == "responsive":
        for token in ["overflow-x: auto", "minmax(0, 1fr)", "env(safe-area-inset-bottom)", "max-width: 430px", "max-width: 820px", "min-width: 1600px", "min-width: 1920px"]:
            add(checks, f"responsive_{token}", token in css)
        add(checks, "stable_mobile_nav", "min-height: 62px" in css and "grid-template-columns: repeat(5" in css)
    release_cleanliness(checks)
    ok = all(item["ok"] for item in checks)
    return {"version": read("VERSION.txt").strip().lstrip("\ufeff"), "suite": kind, "ok": ok, "checks": checks, "failed": [item for item in checks if not item["ok"]]}


def cli(kind: str) -> int:
    result = run(kind)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1
