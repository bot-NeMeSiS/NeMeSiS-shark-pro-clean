from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import app

    data = app.app.test_client().get("/api/runtime-version").get_json()
    for key in [
        "has_v818_automation",
        "has_v844_telegram_quality_filter",
        "has_v845_shark_ai_product_assistant",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v850_live_crests_api_sports_match_detail",
        "has_v851_logo_brand_header_fix",
    ]:
        assert data.get(key) is True, f"{key}={data.get(key)!r}"
    print("V851 V818-V850 compatibility OK")


if __name__ == "__main__":
    main()
