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

texts={p.name:p.read_text(encoding='utf-8', errors='replace') for p in [ROOT/'templates'/'client_login.html', ROOT/'templates'/'register.html', ROOT/'templates'/'admin_login.html']}
required=['autocomplete="on"','autocomplete="username"','autocomplete="current-password"',('Contrase' + chr(241) + 'a')]
missing=[]
for name,text in texts.items():
    for token in ['autocomplete="on"','autocomplete="username"',('Contrase' + chr(241) + 'a')]:
        if token not in text: missing.append(f'{name}:{token}')
if 'autocomplete="new-password"' not in texts['register.html']: missing.append('register:new-password')
if 'autocomplete="current-password"' not in texts['client_login.html']: missing.append('client:current-password')
if 'autocomplete="current-password"' not in texts['admin_login.html']: missing.append('admin:current-password')
ok({'ok':not missing,'missing':missing})
