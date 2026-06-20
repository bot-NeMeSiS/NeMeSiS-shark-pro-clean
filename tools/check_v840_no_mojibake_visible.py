from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V840_PC_VIDEO_LAYOUT_TEXT_NAV_FIX_FINAL"
def ok(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("ok") else 1)
files = list((ROOT / 'templates').glob('*.html')) + [ROOT / 'static' / 'app.css', ROOT / 'app.py']
patterns = [
    '\u00c3', '\u00c2', '\ufffd', 'Contrase?a', 'contrase?a', 'PA?S',
    'd?a', 'd?as', 'se?al', 'se?ales', 'Espa?a', 'Andaluc?a',
    '{{ title or', 'Lorem ipsum'
]
hits = []
for p in files:
    text = p.read_text(encoding='utf-8', errors='replace')
    for pat in patterns:
        if pat in text:
            hits.append({'file': str(p.relative_to(ROOT)), 'pattern': pat})
            break
ok({'ok': not hits, 'hits': hits[:40]})
