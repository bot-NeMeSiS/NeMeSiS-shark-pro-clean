#!/usr/bin/env python3
from pathlib import Path
import json, re, sys
ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL', 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH'
checks = []

def add(name, ok, detail=''):
    checks.append({'name': name, 'ok': bool(ok), 'detail': detail})

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8', errors='ignore')

version = read('VERSION.txt').strip()
app = read('app.py')
base = read('templates/base.html')
css = read('static/app.css')
client = read('templates/client_app_center.html')
home = read('templates/home.html')
admin = read('templates/admin_dashboard.html')
client_map = read('templates/client_navigation_map.html') if (ROOT/'templates/client_navigation_map.html').exists() else ''

add('version_v809', version in {VERSION, 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH'}, version)
add('app_version_v809', (f"APP_VERSION = '{VERSION}'" in app or "APP_VERSION = 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH'" in app))
add('shell_attr_v809', 'data-v809-shell="true"' in base)
add('client_map_route', all(x in app for x in ['@app.route("/app/mapa")','def v809_client_navigation_map_page','client_navigation_map.html']))
add('client_map_template', 'v809-client-map-page' in client_map and '/logout' in client_map and '/calendar?lane=today' in client_map)
add('client_top_map_link', ('<a href="/app/mapa" data-v775-icon="☰">Mapa</a>' in base) or ('<a href="/app/mapa" data-v775-icon="☰">Todo</a>' in base))
add('client_reference_cover', 'v809-reference-cover' in client and 'Todos los accesos' in client)
add('admin_reference_hero', 'v809-admin-reference-hero' in admin and 'Mapa completo' in admin and 'Vista cliente' in admin)
add('css_v809', 'V809 — reference-photo exact UI pass' in css and '.v809-client-map-grid' in css and '.v809-admin-reference-hero' in css)
add('shark_logo_present', (ROOT/'static/img/shark-logo.svg').exists() and 'shark-logo.svg' in base and 'shark-logo.svg' in client and 'shark-logo.svg' in admin)
add('no_client_left_rail', '<aside class="v798-client-rail' not in base and '<aside class="v799-client-rail' not in base)
# Guard against broken query links caused by concatenated URLs.
broken_query_links = []
for tp in (ROOT / 'templates').glob('*.html'):
    txt = tp.read_text(encoding='utf-8', errors='ignore')
    for href in re.findall(r'href=[\"\']([^\"\']+)[\"\']', txt):
        if href.startswith('/') and '?' not in href and re.search(r'(limit|refresh|force|error_id|id|lane|q)=', href):
            broken_query_links.append(f'{tp.name}:{href}')
add('no_broken_query_hrefs', not broken_query_links, ', '.join(broken_query_links[:8]))
# Important client/admin buttons should be reachable from base/dashboard/map
for href in ['/app','/calendar?lane=today','/live','/picks','/shark','/track-record','/telegram','/mi-cuenta','/logout','/admin/map','/admin/users','/admin/matches-sync','/admin/live-depth','/admin/picks','/admin/telegram/command-center','/sports-hub']:
    add(f'button_{href}', href in (base + admin + client_map), href)
# Guardrails against fake stats/text in new sections
bad = ['+12.4% vs ayer','Todos los sistemas OK','ataque inventado','pelota falsa','fake ball','mock live']
joined = (client + admin + client_map + css).lower()
for token in bad:
    add(f'no_fake_{token}', token.lower() not in joined)

ok = all(c['ok'] for c in checks)
print(json.dumps({'ok': ok, 'checks': checks}, indent=2, ensure_ascii=False))
sys.exit(0 if ok else 1)
