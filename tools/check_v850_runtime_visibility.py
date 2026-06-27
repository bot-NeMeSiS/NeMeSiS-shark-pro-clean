from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

VERSION = "V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL"
CURRENT_OR_NEXT = {
    VERSION,
    "V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX",
    "V852_REAL_VIDEO_PRODUCT_PERFECTION_LIVE_PICKS_VISUAL_QA_FINAL",
    "V853_ADMIN_PC_COMMAND_CENTER_REFERENCE_PERFECTION_FINAL",
    "V854_CLIENT_ADMIN_REAL_RENDER_FINAL_POLISH_AND_PRODUCT_QA",
    "V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL",
}


def main():
    assert Path("VERSION.txt").read_text(encoding="utf-8").strip() in CURRENT_OR_NEXT
    assert app.APP_VERSION in CURRENT_OR_NEXT
    client = app.app.test_client()
    payload = client.get("/api/runtime-version").get_json()
    assert payload["app_version"] in CURRENT_OR_NEXT
    assert payload["version_txt"] in CURRENT_OR_NEXT
    assert payload["has_v850_shell"] is True
    assert payload["has_v850_css"] is True
    assert payload["has_v850_live_crests_api_sports_match_detail"] is True
    for key in ["has_v849_full_company_visual_product_experience", "has_v847_company_brain_api_sports_provider_qa", "has_v845_shark_ai_product_assistant", "has_v844_telegram_quality_filter", "has_v818_automation"]:
        assert payload.get(key) is True, key
    for key in ["api_sports_configured", "api_football_configured", "the_odds_configured", "openai_configured", "telegram_configured", "automation_secret_configured", "db_path", "static_app_css_hash", "static_app_css_size"]:
        assert key in payload, key
    print("check_v850_runtime_visibility OK")


if __name__ == "__main__":
    main()
