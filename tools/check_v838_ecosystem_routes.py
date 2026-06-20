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

os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v838_routes.db"))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v838-secret")
import app as nemesis
rules = {str(rule.rule) for rule in nemesis.app.url_map.iter_rules()}
required = ["/app","/partidos","/calendar","/live","/directo","/picks","/match/<match_id>","/shark","/profile","/telegram","/support","/favorites","/track-record","/combis","/mercados","/highlights","/admin/dashboard","/admin/daily-automation","/admin/automation-os","/admin/telegram/command-center","/admin/data-center","/admin/users","/admin/memberships","/admin/payments","/api/automation/master-tick","/api/automation/health-check"]
missing = [r for r in required if r not in rules]
base = read("templates/base.html")
link_required = ["/app","/partidos","/live","/picks","/shark","/profile","/telegram","/support","/admin/telegram/command-center","/admin/data-center","/admin/users","/admin/memberships","/admin/payments"]
missing_links = [x for x in link_required if x not in base]
ok({"ok": not missing and not missing_links, "missing_routes": missing, "missing_base_links": missing_links})
