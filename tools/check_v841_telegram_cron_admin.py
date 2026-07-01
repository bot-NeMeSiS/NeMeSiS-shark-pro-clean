from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v841_cron.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v841-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
no_secret = client.get("/api/automation/master-tick?dry_run=1")
with_secret = client.get("/api/automation/master-tick?secret=codex-v841-secret&dry_run=1")
health = client.get("/api/automation/health-check?secret=codex-v841-secret")
admin = client.get("/admin/telegram/command-center")

payload = {
    "ok": no_secret.status_code == 403 and with_secret.status_code == 200 and health.status_code == 200 and admin.status_code < 500,
    "master_tick_without_secret": no_secret.status_code,
    "master_tick_with_secret_dry_run": with_secret.status_code,
    "health_check_with_secret": health.status_code,
    "admin_telegram_command_center": admin.status_code,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
