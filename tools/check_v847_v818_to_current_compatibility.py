from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v847_compat.db"))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v847-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
runtime = client.get("/api/runtime-version").get_json() or {}
checks = {
    "v818_master_tick_present": runtime.get("has_v818_automation") is True,
    "v844_filter_present": runtime.get("has_v844_telegram_quality_filter") is True,
    "v845_shark_present": runtime.get("has_v845_shark_ai_product_assistant") is True,
    "master_tick_forbidden_without_secret": client.get("/api/automation/master-tick?dry_run=1").status_code == 403,
    "health_check_with_secret": client.get("/api/automation/health-check?secret=codex-v847-secret").status_code == 200,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
