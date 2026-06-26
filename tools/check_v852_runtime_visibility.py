from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXPECTED = "V852_REAL_VIDEO_PRODUCT_PERFECTION_LIVE_PICKS_VISUAL_QA_FINAL"


def main():
    import app
    payload = app.app.test_client().get("/api/runtime-version").get_json()
    assert payload["app_version"] == EXPECTED
    assert payload["version_txt"] == EXPECTED
    for key in [
        "has_v852_real_video_product_perfection",
        "has_v851_logo_brand_header_fix",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v845_shark_ai_product_assistant",
        "has_v844_telegram_quality_filter",
        "has_v818_automation",
    ]:
        assert payload.get(key) is True, f"{key}={payload.get(key)!r}"
    for key in ["api_sports_configured", "api_football_configured", "the_odds_configured", "openai_configured", "telegram_configured", "automation_secret_configured", "static_app_css_hash", "static_app_css_size", "db_path"]:
        assert key in payload, key
    print("V852 runtime visibility OK")


if __name__ == "__main__":
    main()
