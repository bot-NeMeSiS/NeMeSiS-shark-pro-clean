from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
SUCCESSOR = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
V935_SUCCESSOR = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
SUPPORTED_VERSIONS = {VERSION, SUCCESSOR, V935_SUCCESSOR}
FORBIDDEN_RELEASE_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output"}
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def add(checks: list[dict], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def _runtime_and_smoke(checks: list[dict]) -> None:
    keys = ("DB_PATH", "RUN_STARTUP_SCHEDULER_NOW", "TELEGRAM_BOT_TOKEN", "STRIPE_SECRET_KEY", "OPENAI_API_KEY")
    previous = {key: os.environ.get(key) for key in keys}
    with tempfile.TemporaryDirectory(prefix="nemesis_v933_check_", ignore_cleanup_errors=True) as temp_dir:
        os.environ.update({
            "DB_PATH": str(Path(temp_dir) / "v933.sqlite"),
            "RUN_STARTUP_SCHEDULER_NOW": "0",
            "TELEGRAM_BOT_TOKEN": "",
            "STRIPE_SECRET_KEY": "",
            "OPENAI_API_KEY": "",
        })
        try:
            import app as app_module

            app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
            public = app_module.app.test_client()
            client = app_module.app.test_client()
            admin = app_module.app.test_client()
            with client.session_transaction() as session:
                session.update({
                    "user_id": "v933-client-check", "user_name": "Cliente QA",
                    "username": "client_qa", "user_role": "PRO",
                    "membership": "PRO", "user_membership": "PRO",
                })
            with admin.session_transaction() as session:
                session.update({
                    "user_id": "v933-admin-check", "user_name": "Admin QA",
                    "username": "admin_qa", "user_role": "ADMIN",
                    "membership": "ADMIN", "user_membership": "ADMIN",
                })
            runtime_response = public.get("/api/runtime-version")
            runtime = runtime_response.get_json(silent=True) or {}
            add(checks, "runtime_200", runtime_response.status_code == 200, str(runtime_response.status_code))
            runtime_version = str(runtime.get("version") or "")
            add(checks, "runtime_v933", runtime_version in SUPPORTED_VERSIONS, runtime_version)
            add(checks, "runtime_files_match", runtime.get("version_files_match") is True)
            add(checks, "runtime_cache_busting", runtime.get("static_css_cache_busting") is True)
            add(checks, "runtime_service_worker", runtime.get("service_worker_cache_name") == f"NEMESIS_CACHE_{runtime_version.split('_', 1)[0]}")
            flags = [
                "has_v933_reference_parity", "has_v933_public_ui_rebuild",
                "has_v933_client_desktop_rebuild", "has_v933_client_mobile_rebuild",
                "has_v933_admin_rebuild", "has_v933_sports_experience_rebuild",
                "has_v933_component_consistency", "has_v933_accessibility_pass",
                "has_v933_performance_pass", "has_v933_real_data_guard",
            ]
            add(checks, "runtime_flags", all(runtime.get(flag) is True for flag in flags), ",".join(flag for flag in flags if runtime.get(flag) is not True))
            add(checks, "pixel_claim_blocked", runtime.get("v933_pixel_perfect_claim_allowed") is False)
            public_routes = ["/", "/cliente-login", "/registro", "/calendar", "/live", "/picks", "/track-record"]
            client_routes = ["/app", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/profile", "/memberships", "/planes"]
            admin_routes = ["/admin/dashboard", "/admin/telegram/command-center", "/admin/users", "/admin/memberships", "/admin/payments", "/admin/picks", "/admin/matches", "/admin/data-center", "/admin/automation-workforce", "/admin/autonomous-company-sentinel", "/admin/navigation-integrity", "/admin/launch-certification"]
            add(checks, "public_smoke", all(public.get(route, follow_redirects=False).status_code == 200 for route in public_routes))
            add(checks, "client_mock_smoke", all(client.get(route, follow_redirects=False).status_code == 200 for route in client_routes))
            add(checks, "admin_mock_smoke", all(admin.get(route, follow_redirects=False).status_code == 200 for route in admin_routes))
            add(checks, "admin_api_protected", public.get("/api/admin/automation-workforce/status").status_code == 403)
        except Exception as exc:
            add(checks, "runtime_smoke_exception", False, f"{type(exc).__name__}: {str(exc)[:180]}")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _release_clean(checks: list[dict]) -> None:
    deploy = ROOT / "release_output" / "V933_DEPLOY_ROOT_CONTENTS"
    if not deploy.exists():
        add(checks, "deploy_root_pending_build", True, "Audited after clean release build")
        return
    forbidden: list[str] = []
    for path in deploy.rglob("*"):
        rel = path.relative_to(deploy)
        if any(part in FORBIDDEN_RELEASE_PARTS for part in rel.parts):
            forbidden.append(rel.as_posix())
        elif path.is_file() and path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".zip", ".log", ".wal", ".shm"}:
            forbidden.append(rel.as_posix())
    required = ["app.py", "VERSION.txt", "requirements.txt", "templates", "static", "engines", "tools", "reports", "reference_images", "browser_qa", "automation_workforce", ".github/workflows"]
    missing = [item for item in required if not (deploy / item).exists()]
    add(checks, "deploy_forbidden_zero", not forbidden, ", ".join(forbidden[:10]))
    add(checks, "deploy_required_complete", not missing, ", ".join(missing))


def base_checks() -> list[dict]:
    checks: list[dict] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes() if (ROOT / "VERSION.txt").exists() else b""
    version = version_bytes.decode("utf-8", errors="replace").strip().lstrip("\ufeff")
    app = read("app.py")
    base = read("templates/base.html")
    add(checks, "version_exact", version in SUPPORTED_VERSIONS, version)
    add(checks, "version_without_bom", not version_bytes.startswith(b"\xef\xbb\xbf"))
    add(checks, "app_version_exact", f"APP_VERSION = '{version}'" in app)
    add(checks, "v933_css_loaded", all(token in base for token in ("filename='v933_design_tokens.css'", "filename='v933-product.css'", "?v={{ app_version }}")))
    add(checks, "service_worker_v933", f"NEMESIS_CACHE_{version.split('_', 1)[0]}" in app and "cache:'no-store'" in app and "cache:'reload'" in app)
    add(checks, "v929_navigation_preserved", '@app.route("/clientes")' in app and (ROOT / "engines" / "navigation_integrity_engine.py").exists())
    add(checks, "v931_data_truth_preserved", "get_public_home_sports_summary" in app and "v931_safe_dashboard_data" in app)
    add(checks, "v932_sqlite_preserved", "_v932_read_table_rows" in app and "v932_authenticated_request_preflight" in app)
    add(checks, "no_pixel_perfect_static_claim", 'v933_pixel_perfect_claim_allowed": True' not in app)
    return checks


def run(kind: str) -> dict:
    checks = base_checks()
    base = read("templates/base.html")
    css = read("static/v933-product.css")
    tokens = read("static/v933_design_tokens.css")
    ui = read("templates/components/v933_ui.html")
    nav = read("templates/components/v933_navigation.html")
    client_names = ["client_app_center.html", "calendar.html", "live.html", "picks.html", "match_detail.html", "track_record.html", "shark.html", "telegram.html", "profile.html", "membership.html"]
    admin_names = ["admin_dashboard.html", "admin_telegram_command_center.html", "admin_users.html", "admin_memberships.html", "admin_payments.html", "admin_picks.html", "admin_matches_sync.html", "admin_data_center.html", "admin_automation_workforce.html", "admin_autonomous_company_sentinel.html", "admin_navigation_integrity.html", "admin_final_certification.html"]

    if kind == "reference":
        _runtime_and_smoke(checks)
        add(checks, "reference_images_16", len(list((ROOT / "reference_images").rglob("*.png"))) == 16)
        add(checks, "v933_css_substantial", len(css) > 35000, str(len(css)))
    elif kind == "public":
        home = read("templates/home.html")
        add(checks, "single_home_hero", home.count("v933-public-hero") == 1, str(home.count("v933-public-hero")))
        add(checks, "home_v933_components", "components/v933_ui.html" in home and 'data-v933-template="home"' in home)
        add(checks, "home_truth_source", "valid_matches_today" in home and "today_count = matches|length" in home)
        add(checks, "public_shell", "v933_public_shell" in base and "v933-public-topbar" in nav)
    elif kind == "client_desktop":
        for name in client_names:
            source = read(f"templates/{name}")
            add(checks, f"v933_{name}", "components/v933_ui.html" in source and "data-v933-template" in source)
        add(checks, "client_desktop_shell", 'data-nav-zone="client-desktop"' in nav and "v933-client-shell" in base)
        client_nav = nav.split("macro v933_client_navigation", 1)[1].split("endmacro", 1)[0]
        add(checks, "client_no_admin_nav", "/admin/" not in client_nav)
    elif kind == "client_mobile":
        add(checks, "mobile_header", "v933-client-mobile" in nav)
        add(checks, "mobile_bottom_five", "repeat(5" in css and "v933_mobile_bottom_nav" in nav)
        add(checks, "mobile_safe_area", "env(safe-area-inset-bottom" in css)
        add(checks, "desktop_nav_hidden_mobile", ".v933-topbar" in css and "display: none !important" in css)
        add(checks, "mobile_touch_targets", "min-height: 44px" in css)
        add(checks, "mobile_underlap_guard", "var(--v933-mobile-nav)" in css)
    elif kind == "admin":
        for name in admin_names:
            source = read(f"templates/{name}")
            add(checks, f"admin_{name}", "v933-admin-command-center" in source)
        add(checks, "admin_shell", "v933_admin_shell" in base and "v933-admin-sidebar" in nav)
        admin_nav = nav.split("macro v933_admin_sidebar", 1)[1].split("endmacro", 1)[0]
        add(checks, "admin_no_client_nav", "/app" not in admin_nav and "/profile" not in admin_nav)
        add(checks, "admin_top_space", "padding: calc(var(--v933-topbar) + 14px)" in css)
    elif kind == "sports":
        for name in ("calendar.html", "live.html", "picks.html", "match_detail.html", "track_record.html"):
            add(checks, f"sports_{name}", "data-v933-reference" in read(f"templates/{name}"))
        add(checks, "no_live_simulation", "No se simulan marcadores ni minutos" in read("templates/live.html"))
        add(checks, "pick_quality_gate", "partido, mercado, selección y cuota" in read("templates/picks.html").lower())
        add(checks, "track_record_sample_truth", "Sin muestra evaluable" in read("templates/track_record.html"))
        add(checks, "no_render_external_api", "no_render_api_call" in read("app.py"))
    elif kind == "components":
        required = ["page_header", "section_header", "kpi_card", "action_button", "status_chip", "empty_state", "data_table", "filter_tabs", "match_card", "live_card", "pick_card", "plan_card", "profile_card", "provider_state", "team_logo"]
        for macro in required:
            add(checks, f"component_{macro}", f"macro {macro}" in ui)
        for macro in ("v933_public_shell", "v933_client_shells", "v933_admin_shell", "v933_mobile_bottom_nav"):
            add(checks, f"shell_{macro}", f"macro {macro}" in read("templates/components/v933_shells.html") + nav)
        add(checks, "components_used", sum("components/v933_ui.html" in read(f"templates/{path.name}") for path in (ROOT / "templates").glob("*.html")) >= 18)
    elif kind == "accessibility":
        add(checks, "focus_visible", "focus-visible" in tokens)
        add(checks, "reduced_motion", "prefers-reduced-motion" in css)
        add(checks, "forced_colors", "forced-colors" in css)
        add(checks, "aria_navigation", "aria-current" in nav and "aria-label" in nav)
        add(checks, "table_headers", "scope=\"col\"" in ui)
        add(checks, "image_alt", "alt=\"\"" in ui)
    elif kind == "performance":
        app = read("app.py")
        add(checks, "cache_busting", "data-v933-product-version" in base)
        add(checks, "service_worker_network_first_html", "cache:'no-store'" in app)
        add(checks, "service_worker_reload_assets", "cache:'reload'" in app)
        add(checks, "lazy_team_logos", "loading=\"lazy\"" in ui)
        add(checks, "no_render_api_calls", "no_render_api_call" in app and "get_public_home_sports_summary" in app)
        add(checks, "local_icons", "v930-icons.js" in base)
    elif kind == "real_data":
        sources = "\n".join(read(f"templates/{name}") for name in ["home.html", *client_names, *admin_names])
        for token in ("48.732", "125.684", "€18.732", "Arsenal vs Chelsea", "Real Madrid vs Borussia Dortmund", "2.458"):
            add(checks, f"no_reference_demo_{token}", token.lower() not in sources.lower())
        add(checks, "home_consistent_filter", "valid_matches_today" in read("templates/home.html") and "today_count = matches|length" in read("templates/home.html"))
        add(checks, "safe_pick_gate", "No se publica hasta tener partido, mercado, selección y cuota reales" in ui)
        add(checks, "safe_match_gate", "Pendiente de completar" in ui and "match.get('source')" in ui)
        add(checks, "no_fake_roi", "Sin muestra evaluable" in read("templates/track_record.html"))

    _release_clean(checks)
    failed = [item for item in checks if not item["ok"]]
    return {"version": read("VERSION.txt").strip().lstrip("\ufeff"), "suite": kind, "ok": not failed, "checks": checks, "failed": failed}


def cli(kind: str) -> int:
    result = run(kind)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1
