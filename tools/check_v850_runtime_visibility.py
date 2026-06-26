from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

VERSION = "V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL"


def main():
    assert Path("VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert app.APP_VERSION == VERSION
    client = app.app.test_client()
    payload = client.get("/api/runtime-version").get_json()
    assert payload["app_version"] == VERSION
    assert payload["version_txt"] == VERSION
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
