from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXPECTED = "V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX"
CURRENT_OR_NEXT = {
    EXPECTED,
    "V852_REAL_VIDEO_PRODUCT_PERFECTION_LIVE_PICKS_VISUAL_QA_FINAL",
    "V853_ADMIN_PC_COMMAND_CENTER_REFERENCE_PERFECTION_FINAL",
}


def main():
    import app

    client = app.app.test_client()
    response = client.get("/api/runtime-version")
    assert response.status_code == 200, response.status_code
    data = response.get_json()
    assert data["app_version"] in CURRENT_OR_NEXT, data.get("app_version")
    assert data["version_txt"] in CURRENT_OR_NEXT, data.get("version_txt")
    for key in [
        "has_v851_logo_brand_header_fix",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        assert data.get(key) is True, f"{key}={data.get(key)!r}"
    for key in [
        "api_sports_configured",
        "api_football_configured",
        "the_odds_configured",
        "openai_configured",
        "telegram_configured",
        "automation_secret_configured",
        "static_app_css_hash",
        "static_app_css_size",
        "db_path",
    ]:
        assert key in data, key
    assert "SECRET" not in str(data.get("db_path", "")).upper()
    print("V851 runtime visibility OK")


if __name__ == "__main__":
    main()
