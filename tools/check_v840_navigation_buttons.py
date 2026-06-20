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

base=read('templates/base.html')
required=['/app','/partidos','/live','/picks','/shark','/profile','/telegram','/support','/admin/telegram/command-center','/admin/data-center','/admin/users','/admin/memberships','/admin/payments']
missing=[x for x in required if x not in base]
dead=('href="#"' in base or 'href=""' in base)
ok({'ok':not missing and not dead,'missing':missing,'dead_href':dead})
