#!/usr/bin/env python3
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]

def text(path): return (ROOT/path).read_text(encoding='utf-8')
errors=[]
version=text('VERSION.txt').strip()
if not (version.startswith('V775_MOBILE_CLIENT_APP_EXPERIENCE_TOTAL_COMPLETION') or version.startswith('V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER')):
    errors.append(f'VERSION incorrecta: {version}')
base=text('templates/base.html')
css=text('static/app.css')
required_base=['data-v775-shell="true"','data-v775-icon="⌂"','data-v775-icon="☰"','v775MobileShell','ns-keyboard-open']
for item in required_base:
    if item not in base: errors.append(f'base.html falta {item}')
if '<a href="/shark">SHARK</a><a href="/menu">Más</a>' in base:
    errors.append('bottom nav móvil sigue con SHARK + Más saturando')
required_css=['V775_MOBILE_CLIENT_APP_EXPERIENCE_TOTAL_COMPLETION','grid-template-columns:repeat(5','body.ns-keyboard-open .bottom-nav-clean','body.shark-open .bottom-nav-clean','.v774-teams strong:nth-of-type(2){grid-column:2;grid-row:2;display:block!important','max-width:100%;overflow-x:hidden']
for item in required_css:
    if item not in css: errors.append(f'app.css falta {item}')
for path in ['templates/client_app_center.html','templates/client_menu.html','templates/telegram.html','templates/shark.html']:
    s=text(path)
    if 'v774-client-hero' not in s and 'v775-' not in s:
        errors.append(f'{path} no usa layout cliente V774/V775')
# broken links that were visible in old video/code
for path in ROOT.joinpath('templates').glob('*.html'):
    s=path.read_text(encoding='utf-8')
    for bad in ['/sharkq=', '/combistipo=', '/calendarlane=', '/livef=', '/picksfiltro=', '/sharkpick=', '/match-hublane=']:
        if bad in s:
            errors.append(f'enlace roto {bad} en {path.relative_to(ROOT)}')
# page shortcut coverage
for path in ['templates/calendar.html','templates/live.html','templates/picks.html','templates/combis.html','templates/betting_markets.html','templates/highlights.html','templates/track_record.html','templates/sports_hub.html']:
    if 'v775-page-shortcuts' not in text(path):
        errors.append(f'{path} sin accesos cortos V775')
if 'V775_MOBILE_CLIENT_EXPERIENCE_ENABLED=true' not in text('.env.example'):
    errors.append('.env.example sin bandera V775')
if not (ROOT/'reports'/'V775_MOBILE_CLIENT_APP_EXPERIENCE_TOTAL_COMPLETION_REPORT.md').exists():
    errors.append('falta reporte V775')
print('check_v775_mobile_client_app_experience')
if errors:
    for e in errors: print('FAIL:', e)
    sys.exit(1)
print('OK - V775 mobile/client app experience total completion validated')
