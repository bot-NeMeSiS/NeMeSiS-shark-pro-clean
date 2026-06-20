from pathlib import Path
import json, os, sys, re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V838_FULL_PRODUCT_ARCHITECTURE_FINAL_REVIEW_AND_COMPLETION"
def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
def ok(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("ok") else 1)

os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v838_cron.db"))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v838-secret")
import app as nemesis
c = nemesis.app.test_client()
no_secret = c.get("/api/automation/master-tick?dry_run=1")
with_secret = c.get("/api/automation/master-tick?secret=codex-v838-secret&dry_run=1")
health = c.get("/api/automation/health-check?secret=codex-v838-secret")
ok({"ok": no_secret.status_code == 403 and with_secret.status_code == 200 and health.status_code == 200, "master_tick_no_secret": no_secret.status_code, "master_tick_dry_run": with_secret.status_code, "health": health.status_code})
