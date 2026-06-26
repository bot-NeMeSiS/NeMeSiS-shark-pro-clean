from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V853_ADMIN_PC_COMMAND_CENTER_REFERENCE_PERFECTION_FINAL"
CURRENT_OR_NEXT = {VERSION, "V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA"}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def assert_contains(text, needles, label):
    missing = [needle for needle in needles if needle not in text]
    assert not missing, f"{label} missing {missing}"


def runtime_payload():
    import app

    client = app.app.test_client()
    response = client.get("/api/runtime-version")
    assert response.status_code == 200, response.status_code
    return response.get_json()


def check_runtime_visibility():
    payload = runtime_payload()
    assert payload["app_version"] in CURRENT_OR_NEXT, payload.get("app_version")
    assert payload["version_txt"] in CURRENT_OR_NEXT, payload.get("version_txt")
    for key in [
        "has_v853_shell",
        "has_v853_css",
        "has_v853_admin_pc_command_center_reference",
        "has_v852_real_video_product_perfection",
        "has_v851_logo_brand_header_fix",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        assert payload.get(key) is True, f"{key}={payload.get(key)!r}"
    for key in [
        "api_sports_configured",
        "api_football_configured",
        "the_odds_configured",
        "openai_configured",
        "telegram_configured",
        "automation_secret_configured",
        "db_path",
        "static_app_css_hash",
        "static_app_css_size",
    ]:
        assert key in payload, key


def check_admin_shell_sidebar_rail():
    base = read_text("templates/base.html")
    css = read_text("static/app.css")
    assert_contains(base, ["v853-admin-command-strip", "data-v853-shell=\"true\"", "Centro de mando"], "base")
    assert_contains(base, [
        "/admin/dashboard",
        "/admin/data-center",
        "/admin/api-sports",
        "/admin/telegram/command-center",
        "/admin/shark-ai",
        "/admin/daily-automation",
        "/admin/users",
        "/admin/memberships",
        "/admin/payments",
    ], "admin strip")
    assert_contains(css, ["V853 ADMIN PC COMMAND CENTER REFERENCE FINAL START", ".v808-admin-rail", ".v853-admin-command-strip"], "css")
    assert "body[data-v853-shell=\"true\"].ns-admin .bottom-nav" in css
    assert "body[data-v853-shell=\"true\"].ns-admin .floating-shark" in css


def check_admin_page_headers():
    css = read_text("static/app.css")
    assert_contains(css, [".v809-admin-reference-hero", ".v807-admin-hero", ".admin-hero", ".app-hero"], "admin header css")
    for path in [
        "templates/admin_dashboard.html",
        "templates/admin_data_center.html",
        "templates/admin_telegram_command_center.html",
        "templates/admin_shark_center.html",
        "templates/admin_daily_automation.html",
    ]:
        text = read_text(path)
        assert any(token in text for token in ["hero", "panel", "Dashboard", "Centro", "SHARK", "Telegram"]), path


def check_admin_dashboard_command_center():
    text = read_text("templates/admin_dashboard.html")
    assert_contains(text, ["Centro de mando", "Acciones principales", "Estado real", "Mapa completo"], "dashboard")
    for bad in ["diagnsticos", "Segn Render", "Madrid  producción"]:
        assert bad not in text, bad


def check_admin_data_api_sports_command():
    app_py = read_text("app.py")
    assert_contains(app_py, ["/admin/api-sports", "/admin/api-sports-audit", "/api/admin/api-sports/status"], "api sports routes")
    assert (ROOT / "templates/admin_api_sports_audit.html").exists()
    assert (ROOT / "templates/admin_data_center.html").exists()


def check_admin_telegram_command_center():
    app_py = read_text("app.py")
    template = read_text("templates/admin_telegram_command_center.html")
    assert_contains(app_py, ["/admin/telegram/command-center"], "telegram route")
    assert_contains(template, ["Telegram"], "telegram admin template")
    assert (ROOT / "engines/telegram_quality_filter_engine.py").exists()


def check_admin_shark_center():
    app_py = read_text("app.py")
    template = read_text("templates/admin_shark_center.html")
    assert_contains(app_py, ["/admin/shark-ai", "v845_shark_admin_summary"], "shark admin route")
    assert_contains(template, ["SHARK", "IA"], "shark admin template")
    assert (ROOT / "engines/shark_ai_product_assistant_engine.py").exists()


def check_admin_automation_master_tick():
    app_py = read_text("app.py")
    assert_contains(app_py, ["/api/automation/master-tick", "/api/automation/health-check", "AUTOMATION_SECRET"], "automation")
    assert (ROOT / "templates/admin_daily_automation.html").exists()


def check_admin_users_memberships_payments():
    app_py = read_text("app.py")
    assert_contains(app_py, ["/admin/users", "/admin/memberships", "/admin/payments"], "admin business routes")
    for path in ["templates/admin_users.html", "templates/admin_memberships.html", "templates/admin_payments.html"]:
        assert (ROOT / path).exists(), path


def check_admin_pc_visual_reference():
    css = read_text("static/app.css")
    assert_contains(css, [
        "--v853-admin-panel",
        "grid-template-columns: minmax(250px, .72fr) 1.6fr",
        "box-shadow: 0 22px 70px",
        "border-radius: 24px",
    ], "admin pc css")


def check_admin_text_orthography():
    bad_terms = ["diagnsticos", "Segn", "ESPAÃ", "Ã", "Â", "�", "undefined"]
    for path in ["templates/base.html", "templates/admin_dashboard.html", "templates/admin_data_center.html", "templates/admin_telegram_command_center.html", "templates/admin_shark_center.html"]:
        text = read_text(path)
        for bad in bad_terms:
            assert bad not in text, f"{bad} in {path}"


def check_admin_routes_buttons():
    base = read_text("templates/base.html")
    links = [
        "/admin/dashboard",
        "/admin/data-center",
        "/admin/api-sports",
        "/admin/telegram/command-center",
        "/admin/shark-ai",
        "/admin/daily-automation",
        "/admin/users",
        "/admin/memberships",
        "/admin/payments",
        "/api/runtime-version",
    ]
    assert_contains(base, links, "admin command strip links")
    assert "href=\"\"" not in base


def check_v818_to_v852_regression():
    payload = runtime_payload()
    for key in [
        "has_v818_automation",
        "has_v844_telegram_quality_filter",
        "has_v845_shark_ai_product_assistant",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v851_logo_brand_header_fix",
        "has_v852_real_video_product_perfection",
    ]:
        assert payload.get(key) is True, f"{key}={payload.get(key)!r}"


def check_release_cleanliness():
    candidates = [ROOT / "release_output" / ZIP_NAME, ROOT.parent / "releases" / ZIP_NAME]
    zips = [path for path in candidates if path.exists()]
    assert zips, f"ZIP not found: {ZIP_NAME}"
    forbidden_parts = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", "release_output", "releases"}
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".mov"}
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    for name in names:
        parts = set(Path(name).parts)
        assert not (parts & forbidden_parts), name
        suffix = Path(name).suffix.lower()
        assert suffix not in forbidden_suffixes, name
    assert "app.py" in names
    assert "VERSION.txt" in names


CHECKS = {
    "runtime_visibility": check_runtime_visibility,
    "admin_shell_sidebar_rail": check_admin_shell_sidebar_rail,
    "admin_page_headers": check_admin_page_headers,
    "admin_dashboard_command_center": check_admin_dashboard_command_center,
    "admin_data_api_sports_command": check_admin_data_api_sports_command,
    "admin_telegram_command_center": check_admin_telegram_command_center,
    "admin_shark_center": check_admin_shark_center,
    "admin_automation_master_tick": check_admin_automation_master_tick,
    "admin_users_memberships_payments": check_admin_users_memberships_payments,
    "admin_pc_visual_reference": check_admin_pc_visual_reference,
    "admin_text_orthography": check_admin_text_orthography,
    "admin_routes_buttons": check_admin_routes_buttons,
    "v818_to_v852_regression": check_v818_to_v852_regression,
    "release_cleanliness": check_release_cleanliness,
}


def run_check(name):
    CHECKS[name]()
    print(f"V853 {name} OK")
