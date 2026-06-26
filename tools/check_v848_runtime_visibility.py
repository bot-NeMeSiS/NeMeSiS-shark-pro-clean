from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v848_runtime.db"))

import app as nemesis  # noqa: E402

VERSION = "V848_REFERENCE_SHARK_VISUAL_PC_MOBILE_FINAL"
CURRENT_VERSION = "V849_FULL_COMPANY_VISUAL_PRODUCT_EXPERIENCE_ADVANCEMENT"
data = nemesis.app.test_client().get("/api/runtime-version").get_json() or {}
checks = {
    "app_version": data.get("app_version") in {VERSION, CURRENT_VERSION},
    "version_txt": data.get("version_txt") in {VERSION, CURRENT_VERSION},
    "has_v848_shell": data.get("has_v848_shell") is True,
    "has_v848_css": data.get("has_v848_css") is True,
    "has_v848_flag": data.get("has_v848_reference_shark_visual_pc_mobile") is True,
    "v847_kept": data.get("has_v847_company_brain_api_sports_provider_qa") is True,
    "v845_kept": data.get("has_v845_shark_ai_product_assistant") is True,
    "v844_kept": data.get("has_v844_telegram_quality_filter") is True,
    "v818_kept": data.get("has_v818_automation") is True,
    "provider_flags": all(k in data for k in ["api_sports_configured", "api_football_configured", "the_odds_configured", "openai_configured", "telegram_configured", "automation_secret_configured"]),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
