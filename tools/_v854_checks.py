from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA"
CURRENT_OR_NEXT = {VERSION, "V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL"}
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


def text(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def contains(blob, needles, label):
    missing = [needle for needle in needles if needle not in blob]
    assert not missing, f"{label} missing {missing}"


def runtime():
    import app

    response = app.app.test_client().get("/api/runtime-version")
    assert response.status_code == 200, response.status_code
    return response.get_json()


def check_runtime_visibility():
    payload = runtime()
    assert payload["app_version"] in CURRENT_OR_NEXT, payload.get("app_version")
    assert payload["version_txt"] in CURRENT_OR_NEXT, payload.get("version_txt")
    for key in [
        "has_v854_shell",
        "has_v854_css",
        "has_v854_client_admin_real_render_final_polish",
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
    for key in ["api_sports_configured", "api_football_configured", "the_odds_configured", "openai_configured", "telegram_configured", "automation_secret_configured", "db_path", "static_app_css_hash", "static_app_css_size"]:
        assert key in payload, key


def check_client_premium_final():
    base = text("templates/base.html")
    css = text("static/app.css")
    for route in ["/app", "/partidos", "/live", "/picks", "/shark", "/telegram", "/profile", "/support"]:
        assert route in base, route
    contains(css, ["body[data-v854-shell=\"true\"]:not(.ns-admin) .v799-card", ".v852-live-empty-diagnostic", "padding-bottom: calc(env(safe-area-inset-bottom) + 104px)"], "client css")


def check_admin_command_center_final():
    base = text("templates/base.html")
    css = text("static/app.css")
    contains(base, ["v853-admin-command-strip", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"], "admin command links")
    contains(css, ["body[data-v854-shell=\"true\"].ns-admin .v853-admin-command-strip", ".floating-shark", "display: none !important"], "admin css")


def check_live_api_sports_final():
    app_py = text("app.py")
    contains(app_py, ["/live", "/directo", "/api/admin/api-sports/status", "api_sports_provider_engine", "live_match_experience_engine"], "live api sports")
    assert (ROOT / "engines/api_sports_provider_engine.py").exists()
    assert (ROOT / "engines/live_match_experience_engine.py").exists()


def check_picks_quality_history_final():
    app_py = text("app.py")
    combined = "\n".join([app_py, text("templates/picks.html"), text("templates/client_app_center.html"), text("templates/track_record.html")])
    contains(app_py, ["/picks", "/track-record"], "picks routes")
    assert any(token in combined for token in ["Cuotas pendientes", "cuotas pendientes", "Cuota pendiente"]), "odds pending copy"
    assert any(token in combined for token in ["Sin picks activos", "sin picks activos", "No hay picks"]), "empty picks copy"
    assert (ROOT / "templates/picks.html").exists()
    assert (ROOT / "templates/track_record.html").exists()


def check_logos_crests_branding_final():
    base = text("templates/base.html")
    css = text("static/app.css")
    contains(base, ["partials/brand_logo.html", "shark-logo.svg"], "brand")
    contains(css, ["team-logo", "team-crest", "league-logo", "object-fit: contain"], "crest css")
    assert (ROOT / "templates/partials/brand_logo.html").exists()
    assert (ROOT / "engines/crest_logo_experience_engine.py").exists()


def check_shark_ai_final_product():
    app_py = text("app.py")
    contains(app_py, ["/shark", "/api/shark/ask", "/admin/shark-ai", "shark_ai_product_assistant_engine"], "shark")
    assert (ROOT / "engines/shark_ai_product_assistant_engine.py").exists()


def check_telegram_final_product():
    app_py = text("app.py")
    contains(app_py, ["/admin/telegram/command-center", "telegram_quality_filter_engine", "/api/automation/master-tick"], "telegram")
    assert (ROOT / "engines/telegram_quality_filter_engine.py").exists()


def check_visual_pc_mobile_final():
    css = text("static/app.css")
    contains(css, ["V854 CLIENT ADMIN REAL RENDER FINAL POLISH START", "--v854-line", "text-wrap: balance", "safe-area-inset-bottom"], "visual css")


def check_text_orthography_global():
    bad = ["Ã", "Â", "", "lo primo", "Result ados", "EspaÁa", "undefined"]
    for path in ["templates/base.html", "templates/client_app_center.html", "templates/live.html", "templates/picks.html", "templates/admin_dashboard.html", "templates/admin_data_center.html"]:
        blob = text(path)
        for token in bad:
            assert token not in blob, f"{token} in {path}"


def check_routes_total_flow():
    base = text("templates/base.html")
    app_py = text("app.py")
    for route in ["/app", "/partidos", "/live", "/picks", "/shark", "/telegram", "/profile", "/support", "/admin/dashboard", "/admin/data-center", "/admin/api-sports", "/admin/telegram/command-center", "/admin/shark-ai", "/admin/daily-automation", "/admin/users", "/admin/memberships", "/admin/payments"]:
        assert route in base or route in app_py, route
    assert 'href=""' not in base


def check_v818_to_v853_regression():
    payload = runtime()
    for key in ["has_v818_automation", "has_v844_telegram_quality_filter", "has_v845_shark_ai_product_assistant", "has_v847_company_brain_api_sports_provider_qa", "has_v850_live_crests_api_sports_match_detail", "has_v851_logo_brand_header_fix", "has_v852_real_video_product_perfection", "has_v853_admin_pc_command_center_reference"]:
        assert payload.get(key) is True, f"{key}={payload.get(key)!r}"


def check_release_cleanliness():
    paths = [ROOT / "release_output" / ZIP_NAME, ROOT.parent / "releases" / ZIP_NAME]
    found = [path for path in paths if path.exists()]
    assert found, ZIP_NAME
    forbidden_parts = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", "release_output", "releases"}
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".mov"}
    with zipfile.ZipFile(found[0]) as zf:
        names = zf.namelist()
    for name in names:
        parts = set(Path(name).parts)
        assert not (parts & forbidden_parts), name
        assert Path(name).suffix.lower() not in forbidden_suffixes, name
    assert "app.py" in names
    assert "VERSION.txt" in names


CHECKS = {
    "runtime_visibility": check_runtime_visibility,
    "client_premium_final": check_client_premium_final,
    "admin_command_center_final": check_admin_command_center_final,
    "live_api_sports_final": check_live_api_sports_final,
    "picks_quality_history_final": check_picks_quality_history_final,
    "logos_crests_branding_final": check_logos_crests_branding_final,
    "shark_ai_final_product": check_shark_ai_final_product,
    "telegram_final_product": check_telegram_final_product,
    "visual_pc_mobile_final": check_visual_pc_mobile_final,
    "text_orthography_global": check_text_orthography_global,
    "routes_total_flow": check_routes_total_flow,
    "v818_to_v853_regression": check_v818_to_v853_regression,
    "release_cleanliness": check_release_cleanliness,
}


def run_check(name):
    CHECKS[name]()
    print(f"V854 {name} OK")
