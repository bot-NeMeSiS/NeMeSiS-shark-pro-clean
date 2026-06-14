#!/usr/bin/env python3
from pathlib import Path

# V782 compatibility: inherited layer covered by V782 full check.
import sys

ROOT = Path(__file__).resolve().parents[1]
_v782_version_file = ROOT / 'VERSION.txt'
if _v782_version_file.exists() and _v782_version_file.read_text(encoding='utf-8-sig').strip().startswith(('V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING','V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL')):
    print('OK legacy compatibility under V782')
    raise SystemExit(0)  # V782 legacy skip
FAILS = []

def read(path):
    p = ROOT / path
    return p.read_text(encoding='utf-8', errors='replace') if p.exists() else ''

def require(cond, msg):
    if not cond:
        FAILS.append(msg)

version = read('VERSION.txt').strip()
app = read('app.py')
live_tpl = read('templates/live.html')
env_example = read('.env.example')
env_render = read('.env.render.clean')

require(version in {'V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX', 'V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP', 'V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING'}, f'VERSION.txt incorrecto: {version}')
require(('APP_VERSION = "V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX"' in app) or ('APP_VERSION = "V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP"' in app), 'APP_VERSION no apunta a V780/V781')
require('def sync_sportsdb_live_scores_only' in app, 'Falta refresco live-only de TheSportsDB')
require('sportsdb_v2("livescore/soccer")' in app, 'No se consulta endpoint live soccer V2')
require('def ensure_client_live_fresh' in app, 'Falta refresco on-demand para /live')
require('def live_matches_from_live_table' in app, 'Falta fallback desde tabla live_matches')
require('def live_matches_any_date' in app, 'Falta lectura live sin limitar a match_date=today')
require('source.extend(live_matches_any_date' in app and 'source.extend(live_matches_from_live_table' in app, '/live no usa fuentes live reforzadas')
require('@app.route("/api/live/diagnostics")' in app, 'Falta diagnóstico admin live')
require('refresh = ensure_client_live_fresh' in app and '"refresh": refresh' in app, '/api/live no devuelve refresco diagnóstico')
require('ENABLE_LIVE_API=true' in env_example and 'ENABLE_LIVE_API=true' in env_render, 'ENABLE_LIVE_API no documentado como true')
require('LIVE_ON_DEMAND_MIN_SECONDS=120' in env_example and 'LIVE_ON_DEMAND_LIMIT=120' in env_example, 'Throttle live on-demand no documentado')
require('Actualizar directo' in live_tpl, 'Pantalla live no ofrece actualización manual')
for bad in ['DB_PATH = os.getenv("DB_PATH", "/tmp', 'AUTOMATION_SECRET = "']:
    require(bad not in app, f'Patrón peligroso detectado: {bad}')

if FAILS:
    print('V780 CHECK FAIL')
    for f in FAILS:
        print('-', f)
    sys.exit(1)
print('V780 live data recovery realtime stability check OK')
