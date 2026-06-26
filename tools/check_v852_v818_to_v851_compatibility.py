import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import app
    payload = app.app.test_client().get("/api/runtime-version").get_json()
    for key in ["has_v818_automation", "has_v844_telegram_quality_filter", "has_v845_shark_ai_product_assistant", "has_v847_company_brain_api_sports_provider_qa", "has_v850_live_crests_api_sports_match_detail", "has_v851_logo_brand_header_fix", "has_v852_real_video_product_perfection"]:
        assert payload.get(key) is True, f"{key}={payload.get(key)!r}"
    print("V852 V818-V851 compatibility OK")


if __name__ == "__main__":
    main()
