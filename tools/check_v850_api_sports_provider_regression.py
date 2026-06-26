from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from engines.api_sports_provider_engine import api_sports_safe_request, get_api_sports_status, sync_api_sports_live


def main():
    status = get_api_sports_status(None)
    assert status["api_sports_cache_enabled"] is True
    assert status["api_sports_credit_guard_enabled"] is True
    assert status["usage_guard"]["no_page_render_calls"] is True
    assert sync_api_sports_live(dry_run=True)["dry_run"] is True
    assert api_sports_safe_request("fixtures", {"live": "all"}, dry_run=True)["dry_run"] is True
    client = app.app.test_client()
    runtime = client.get("/api/runtime-version").get_json()
    assert "api_sports_configured" in runtime and "usage_guard" in runtime
    print("check_v850_api_sports_provider_regression OK")


if __name__ == "__main__":
    main()
