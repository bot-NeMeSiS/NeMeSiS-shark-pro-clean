from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V930_CANONICAL_REFERENCE_VISUAL_PARITY_ADMIN_CLIENT_MOBILE_FINAL"
V931_VERSION = "V931_PRODUCTION_CLIENT_ROUTES_AND_HOME_DATA_CONSISTENCY_HOTFIX_FINAL"
V932_VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
V933_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
ALLOWED_VERSIONS = {VERSION, V931_VERSION, V932_VERSION, V933_VERSION}
FORBIDDEN_RELEASE_NAMES = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output"}
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def add(checks: list[dict], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def _runtime_checks(checks: list[dict]) -> None:
    old = {key: os.environ.get(key) for key in ("DB_PATH", "TELEGRAM_BOT_TOKEN", "AUTOMATION_SECRET", "STRIPE_SECRET_KEY", "OPENAI_API_KEY")}
    with tempfile.TemporaryDirectory(prefix="nemesis_v930_runtime_") as temp_dir:
        os.environ["DB_PATH"] = str(Path(temp_dir) / "v930.sqlite")
        for key in ("TELEGRAM_BOT_TOKEN", "AUTOMATION_SECRET", "STRIPE_SECRET_KEY", "OPENAI_API_KEY"):
            os.environ[key] = ""
        try:
            from app import app

            app.config.update(TESTING=True)
            response = app.test_client().get("/api/runtime-version")
            payload = response.get_json(silent=True) or {}
            add(checks, "runtime_200", response.status_code == 200, str(response.status_code))
            add(checks, "runtime_version_v930_or_successor", payload.get("version") in ALLOWED_VERSIONS, str(payload.get("version")))
            add(checks, "runtime_files_match", payload.get("version_files_match") is True)
            add(checks, "runtime_aligned", payload.get("deployment_alignment_status") == "aligned_local_files")
            add(checks, "runtime_cache_busting", payload.get("static_css_cache_busting") is True)
            expected_cache = f"NEMESIS_CACHE_{str(payload.get('version') or '').split('_', 1)[0]}"
            add(checks, "runtime_service_worker", payload.get("service_worker_cache_name") == expected_cache)
        except Exception as exc:
            add(checks, "runtime_local", False, f"{exc.__class__.__name__}: {str(exc)[:180]}")
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _release_clean(checks: list[dict]) -> None:
    deploy = ROOT / "release_output" / "V930_DEPLOY_ROOT_CONTENTS"
    if not deploy.exists():
        add(checks, "deploy_root_pending_build", True, "se audita después del build")
        return
    forbidden: list[str] = []
    for path in deploy.rglob("*"):
        rel = path.relative_to(deploy)
        if any(part in FORBIDDEN_RELEASE_NAMES for part in rel.parts) or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".zip", ".log", ".wal", ".shm"}:
            forbidden.append(rel.as_posix())
    add(checks, "deploy_root_forbidden_zero", not forbidden, ", ".join(forbidden[:8]))


def _base_checks() -> list[dict]:
    checks: list[dict] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes() if (ROOT / "VERSION.txt").exists() else b""
    current = version_bytes.decode("utf-8", errors="replace").strip().lstrip("\ufeff")
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/v930-canonical.css")
    add(checks, "version_v930_or_successor", current in ALLOWED_VERSIONS, current)
    add(checks, "version_without_bom", not version_bytes.startswith(b"\xef\xbb\xbf"))
    add(checks, "app_version_exact", f"APP_VERSION = '{current}'" in app)
    add(checks, "v930_css_loaded", "filename='v930-canonical.css'" in base and "?v={{ app_version }}" in base)
    add(checks, "service_worker_v930_or_successor", f"NEMESIS_CACHE_{current.split('_', 1)[0]}" in app and "cache:'no-store'" in app and "cache:'reload'" in app)
    add(checks, "canonical_css_substantial", len(css) > 18000, str(len(css)))
    for flag in (
        "has_v930_canonical_visual_parity",
        "has_v930_admin_visual_parity",
        "has_v930_client_desktop_visual_parity",
        "has_v930_client_mobile_visual_parity",
        "has_v930_component_consolidation",
        "has_v930_real_data_presentation_guard",
        "has_v930_second_visual_correction_pass",
    ):
        add(checks, flag, flag in app)
    add(checks, "v929_clientes_preserved", '@app.route("/clientes")' in app and "v929_clients_legacy_alias" in app)
    add(checks, "v929_navigation_engine_preserved", (ROOT / "engines" / "navigation_integrity_engine.py").exists())
    add(checks, "no_pixel_perfect_claim", 'v930_pixel_perfect_claim_allowed": True' not in app)
    return checks


def run(kind: str) -> dict:
    checks = _base_checks()
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/v930-canonical.css")
    ui = read("templates/components/v930_ui.html")
    nav = read("templates/components/v930_navigation.html")
    client_files = ["client_app_center.html", "calendar.html", "live.html", "picks.html", "track_record.html", "shark.html", "telegram.html", "profile.html", "membership.html", "match_detail.html"]
    admin_files = ["admin_dashboard.html", "admin_telegram_command_center.html", "admin_users.html", "admin_memberships.html", "admin_payments.html", "admin_picks.html", "admin_matches_sync.html", "admin_data_center.html", "admin_automation_center.html", "admin_navigation_integrity.html", "admin_final_certification.html", "admin_final_qa.html", "admin_system.html"]

    if kind == "canonical":
        _runtime_checks(checks)
        add(checks, "reference_images_16", len(list((ROOT / "reference_images").rglob("*.png"))) == 16)
        add(checks, "four_shells", all(token in nav for token in ("canonical_public_shell", "canonical_client_desktop_shell", "canonical_client_mobile_shell", "canonical_admin_shell")))
        home = read("templates/home.html")
        legacy_single_hero = home.count("v928-home-hero") == 2 and "{% if current_user %}" in home and "{% else %}" in home
        v933_single_hero = home.count("v933-public-hero") == 1
        add(checks, "single_home_hero", legacy_single_hero or v933_single_hero)
        add(checks, "desktop_dead_space_guard", "padding: calc(var(--v930-topbar) + 14px)" in css)
    elif kind == "admin":
        for name in admin_files:
            source = read(f"templates/{name}")
            add(checks, f"admin_active_{name}", "v930-admin" in source or "v928-admin-command-center" in source)
        sidebar = nav.split("macro canonical_admin_sidebar", 1)[1].split("endmacro", 1)[0]
        add(checks, "admin_without_client_nav", "/app" not in sidebar and "/profile" not in sidebar)
        add(checks, "admin_shell_fixed", "position: fixed" in css and "--v930-sidebar" in css)
        add(checks, "admin_top_gap_zero", "padding-top: 0 !important" in css)
    elif kind == "client":
        for name in client_files:
            source = read(f"templates/{name}")
            add(checks, f"client_v930_{name}", "components/v930_ui.html" in source and "v930-client-page" in source)
        rendered_words = "\n".join(read(f"templates/{name}") for name in client_files)
        for forbidden in ("provider exception", "cache hit", "runtime técnico", "secret status"):
            add(checks, f"client_no_{forbidden}", forbidden.lower() not in rendered_words.lower())
        add(checks, "client_madrid_time", "Hora Madrid" in read("templates/client_app_center.html"))
        add(checks, "client_safe_provider_copy", "Disponibilidad de datos" in ui and "Última actualización" in ui)
    elif kind == "mobile":
        add(checks, "mobile_header", "canonical_client_mobile_shell" in nav and "v930-mobile-header" in nav)
        add(checks, "mobile_bottom_five", "repeat(5" in css and "canonical_mobile_bottom_nav" in nav)
        add(checks, "mobile_safe_area", "env(safe-area-inset-bottom" in css)
        add(checks, "desktop_nav_hidden_mobile", ".v930-client-desktop-chrome" in css and "display: none !important" in css)
        add(checks, "mobile_breakpoints", "max-width: 760px" in css and "max-width: 380px" in css)
        add(checks, "mobile_no_underlap", "var(--v930-mobile-nav)" in css)
        add(checks, "mobile_overflow_guard", "overflow-x: auto" in css and "min-width: 0" in css)
    elif kind == "components":
        required = [
            "canonical_page_header", "canonical_section_header", "canonical_kpi_card", "canonical_action_button",
            "canonical_status_chip", "canonical_empty_state", "canonical_table_shell", "canonical_filter_tabs",
            "canonical_match_card", "canonical_live_card", "canonical_pick_card", "canonical_plan_card",
            "canonical_profile_card", "canonical_provider_state", "canonical_logo_fallback",
        ]
        for macro in required:
            add(checks, f"component_{macro}", f"macro {macro}" in ui)
        for macro in ("canonical_public_shell", "canonical_client_desktop_shell", "canonical_client_mobile_shell", "canonical_admin_shell", "canonical_client_topbar", "canonical_admin_topbar", "canonical_admin_sidebar", "canonical_mobile_bottom_nav"):
            add(checks, f"component_{macro}", f"macro {macro}" in nav)
        active_imports = sum("components/v930_ui.html" in read(f"templates/{p.name}") for p in (ROOT / "templates").glob("*.html"))
        add(checks, "components_used_in_real_templates", active_imports >= 20, str(active_imports))
    elif kind == "real_data":
        targets = "\n".join(read(f"templates/{name}") for name in client_files + admin_files)
        for token in ("48.732", "125.684", "€18.732", "Arsenal vs Chelsea", "Real Madrid vs Borussia Dortmund"):
            add(checks, f"no_reference_demo_{token}", token.lower() not in targets.lower())
        add(checks, "pick_publish_gate", "blocked_incomplete_pick" in app)
        add(checks, "no_render_external_calls", 'v928_page_render_external_calls": False' in app)
        add(checks, "client_provider_copy_safe", "Disponibilidad de datos" in ui and "Fuente</dt>" not in ui)
        add(checks, "no_fake_roi_chart", "v793-chart-fake" not in read("templates/track_record.html"))
        add(checks, "no_fake_match_fallback", "No se muestran partidos de ejemplo" in read("templates/calendar.html"))

    _release_clean(checks)
    ok = all(item["ok"] for item in checks)
    return {"version": read("VERSION.txt").strip().lstrip("\ufeff"), "suite": kind, "ok": ok, "checks": checks, "failed": [item for item in checks if not item["ok"]]}


def cli(kind: str) -> int:
    result = run(kind)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1
