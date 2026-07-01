from pathlib import Path
import json, os, sys, re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V840_PC_VIDEO_LAYOUT_TEXT_NAV_FIX_FINAL"
def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
def ok(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("ok") else 1)

css=read('static/app.css')
required=['body[data-v840-shell="true"].ns-admin .bottom-nav-clean','body[data-v840-shell="true"].ns-admin .v825-public-floating-shark','body[data-v840-shell="true"][data-ns-route="/shark"] .shark-widget']
missing=[x for x in required if x not in css]
ok({'ok':not missing,'missing':missing})
