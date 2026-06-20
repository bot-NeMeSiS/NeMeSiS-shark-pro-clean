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

base = read("templates/base.html")
app_py = read("app.py")
problems = []
if "csrf-token" not in base: problems.append("missing_csrf_meta")
if "/api/automation/master-tick" not in app_py: problems.append("missing_master_tick")
if "automation_secret" not in app_py.lower(): problems.append("missing_secret_guard_reference")
if "TELEGRAM_BOT_TOKEN" in base: problems.append("secret_in_template")
if "THE_ODDS_API_KEY" in base: problems.append("odds_secret_in_template")
ok({"ok": not problems, "problems": problems})
