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
required = ["data-v838-shell", "bottom-nav-clean", "v829-mobile-quick", "v825-public-floating-shark", "env(safe-area-inset-bottom", "overflow-x:hidden", "grid-template-columns:repeat(5"]
missing = [x for x in required if x not in base + css]
admin_leak = "body[data-v838-shell=\"true\"].ns-admin .bottom-nav-clean" not in css
ok({"ok": not missing and not admin_leak, "missing": missing, "admin_leak_protection": not admin_leak})
