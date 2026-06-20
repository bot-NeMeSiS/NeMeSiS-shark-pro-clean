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

css=read('static/app.css'); base=read('templates/base.html')
required=['data-v840-shell','--v840-rail-width','margin-left:calc(var(--v840-rail-width)','margin-left:calc(var(--v840-admin-rail-width)','padding-left:0!important','@media(max-width:980px)']
missing=[x for x in required if x not in css+base]
ok({'ok':not missing,'missing':missing})
