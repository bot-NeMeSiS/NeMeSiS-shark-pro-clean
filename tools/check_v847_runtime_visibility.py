from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v847_check.db"))

import app as nemesis  # noqa: E402

VERSION = "V847_COMPANY_BRAIN_API_SPORTS_DATA_PROVIDER_AND_PRODUCT_QA_FINAL"

client = nemesis.app.test_client()
data = client.get("/api/runtime-version").get_json() or {}
checks = {
    "app_version": data.get("app_version") == VERSION,
    "version_txt": data.get("version_txt") == VERSION,
    "has_v847_shell": data.get("has_v847_shell") is True,
    "has_v847_css": data.get("has_v847_css") is True,
    "runtime_provider_flags": all(k in data for k in ["api_sports_configured", "api_football_configured", "the_odds_configured", "provider_active", "last_sync", "last_error", "usage_guard"]),
    "compat_v845": data.get("has_v845_shark_ai_product_assistant") is True,
    "compat_v844": data.get("has_v844_telegram_quality_filter") is True,
    "compat_v818": data.get("has_v818_automation") is True,
}
failed = [name for name, ok in checks.items() if not ok]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
