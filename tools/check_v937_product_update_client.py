from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[ROOT/'static/v937-product-client.css',ROOT/'static/v937-product-client.js',ROOT/'reports/V937_PRODUCT_UPDATE_CLIENT_01.md']
missing=[str(p.relative_to(ROOT)) for p in required if not p.exists()]
base=ROOT/'templates/base.html'
if missing or not base.exists():
    print('V937 CLIENT UPDATE CHECK: FAIL',missing)
    raise SystemExit(1)
text=base.read_text(encoding='utf-8',errors='ignore')
for marker in ('v937-product-client.css','v937-product-client.js'):
    if marker not in text:
        print('V937 CLIENT UPDATE CHECK: FAIL missing link',marker)
        raise SystemExit(1)
print('V937 CLIENT UPDATE CHECK: OK')
