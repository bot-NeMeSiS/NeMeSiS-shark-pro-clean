from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


def main():
    client = app.app.test_client()
    payload = client.get("/api/runtime-version").get_json()
    for key in [
        "has_v818_automation",
        "has_v844_telegram_quality_filter",
        "has_v845_shark_ai_product_assistant",
        "has_v847_company_brain_api_sports_provider_qa",
        "has_v848_reference_shark_visual_pc_mobile",
        "has_v849_full_company_visual_product_experience",
        "has_v850_live_crests_api_sports_match_detail",
    ]:
        assert payload.get(key) is True, key
    assert "db_path" in payload
    print("check_v850_v818_to_v849_compatibility OK")


if __name__ == "__main__":
    main()
