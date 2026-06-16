#!/usr/bin/env python3
from pathlib import Path
import re, sys, json
ROOT = Path(__file__).resolve().parents[1]
checks=[]

def add(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})

version=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
app=(ROOT/'app.py').read_text(encoding='utf-8')
base=(ROOT/'templates/base.html').read_text(encoding='utf-8')
css=(ROOT/'static/app.css').read_text(encoding='utf-8')
add('version_v808', version in {'V808_FULL_ECOSYSTEM_REFERENCE_UI_ADMIN_CLIENT_FINAL_PERFECTION','V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL', 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH', 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL'}, version)
add('app_version_v808', ('V808_FULL_ECOSYSTEM_REFERENCE_UI_ADMIN_CLIENT_FINAL_PERFECTION' in app or 'V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL' in app or 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH' in app or 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL' in app))
add('shark_logo_asset', (ROOT/'static/img/shark-logo.svg').exists())
add('brand_uses_shark_logo', 'static/img/shark-logo.svg' in base and 'v808-shark-mark' in base)
add('admin_rail_present', 'v808-admin-rail' in base and 'v808-admin-dock' in base)
add('client_left_rail_removed', '<aside class="v798-client-rail' not in base and '<aside class="v799-client-rail' not in base)
add('client_bottom_has_shark', '<a href="/shark" data-v775-icon="◥">SHARK</a>' in base)
add('admin_map_route', '@app.route("/admin/map")' in app and 'admin_navigation_map.html' in app)
add('missing_admin_routes_restored', all(r in app for r in ['@app.route("/admin/support-center")','@app.route("/admin/pick-performance")','@app.route("/admin/betting-center")','@app.route("/admin/intelligence-engine")']))
add('admin_api_buttons_restored', all(r in app for r in ['@app.route("/api/betting/generate")','@app.route("/api/betting/convert-to-pick")','@app.route("/api/telegram/enqueue-recommendations")']))
for broken in ['generatelimit=40','recommendationsrefresh=1','convert-to-pickid=','enqueue-recommendationsforce=1']:
    add(f'no_broken_link_{broken}', broken not in ''.join(p.read_text(encoding='utf-8', errors='ignore') for p in (ROOT/'templates').glob('*.html')))
add('v808_css_present', 'V808 — final reference UI pass' in css and '.v808-admin-map-cards' in css)
# Ensure all explicit v566 admin items are now routable or intentionally variable-free exact routes
routes=set(re.findall(r"@app\.route\(['\"]([^'\"]+)", app))
links=set(re.findall(r"['\"](/admin/[^'\"]+)['\"]", app))
missing=[]
for link in sorted(links):
    if '<' in link: continue
    base_link=link.split('?')[0]
    if base_link not in routes and base_link not in {'/admin/telegram/diagnostics'}:
        missing.append(base_link)
add('v566_admin_links_registered', not missing, ', '.join(missing[:20]))
ok=all(c['ok'] for c in checks)
print(json.dumps({"ok": ok, "checks": checks}, indent=2, ensure_ascii=False))
sys.exit(0 if ok else 1)
