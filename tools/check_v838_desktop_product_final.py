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
css = read("static/app.css")
required = ["v828-client-rail", "v808-admin-rail", "@media(min-width:981px)", "body[data-v838-shell=\"true\"] .bottom-nav-clean{display:none!important}", "ns-admin"]
missing = [x for x in required if x not in base + css]
ok({"ok": not missing, "missing": missing})
