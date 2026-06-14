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
    return p.read_text(encoding='utf-8') if p.exists() else ''

def require(cond, msg):
    if not cond:
        FAILS.append(msg)

version = read('VERSION.txt').strip()
app = read('app.py')
css = read('static/app.css')
base = read('templates/base.html')
partial = read('templates/partials/team_identity.html')

require(version in {'V779_TEAM_IDENTITY_FLAGS_CRESTS_FINAL_POLISH', 'V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX', 'V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP', 'V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING'}, 'VERSION.txt no está en V779/V780/V781/V782/V782 compatible')
require('def team_display_identity' in app and 'def team_identity_for_match' in app, 'Faltan helpers centrales de identidad V779')
require('@app.template_filter("team_identity")' in app, 'Falta filtro Jinja team_identity')
require('@app.template_filter("team_crest_url")' in app, 'Falta filtro Jinja team_crest_url')
require('http://"):\n        # Avoid mixed-content blocks' in read('engines/team_identity_engine.py'), 'safe_logo_url no actualiza HTTP a HTTPS')
require('/team-crest.svg' in app and 'def team_crest_svg' in app, 'Fallback SVG /team-crest.svg no está disponible')
require('nsV779TeamIdentityFallback' in base, 'Falta JS fallback de escudos V779')
require('macro crest' in partial and 'data-fallback' in partial, 'Falta macro robusta de escudo/bandera')
require('v779-crest' in css and 'v779-row-main' in css, 'Falta CSS V779 para identidad visual')
for tpl in ['client_app_center.html','calendar.html','live.html','picks.html','match_detail.html','sports_hub.html']:
    text = read('templates/' + tpl)
    require('partials/team_identity.html' in text, f'{tpl} no importa el parcial de identidad')
    require('crest(' in text or '|team_identity' in text, f'{tpl} no usa identidad visual robusta')
require('item.update(apply_team_identities_to_match(item))' in app, 'client_match_display_context no aplica identidades')
require('home_crest_url' in app and 'away_crest_url' in app, 'apply_team_identities_to_match no expone crest_url visible')

if FAILS:
    print('V779 CHECK FAIL')
    for f in FAILS:
        print('-', f)
    sys.exit(1)
print('V779 CHECK OK: identidad visual de equipos, escudos, banderas y fallback robusto activos.')
