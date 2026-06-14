#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
version=(ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()
if not version.startswith('V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY'):
    errors.append(f'VERSION.txt no es V778: {version}')
base=(ROOT/'templates/base.html').read_text(encoding='utf-8')
css=(ROOT/'static/app.css').read_text(encoding='utf-8')
app=(ROOT/'app.py').read_text(encoding='utf-8')
if 'v777-client-rail' in base:
    errors.append('base.html conserva v777-client-rail duplicado')
for token in ['data-v778-shell="true"','bottom-nav-clean','nav-clean']:
    if token not in base:
        errors.append(f'falta {token} en base.html')
for token in ['V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY','.v777-client-rail','.v775-mobile-command','.v775-page-shortcuts']:
    if token not in css:
        errors.append(f'falta CSS V778/control {token}')
for token in ['def jinja_madrid_datetime_label','def v778_client_product_organization_context','/api/client/product-organization','/api/admin/client-organization-quality']:
    if token not in app:
        errors.append(f'falta {token} en app.py')
required_templates={
    'client_app_center.html':['v778-home-hero','Ruta recomendada de hoy','Europe/Madrid','match_madrid_context'],
    'client_menu.html':['Todo visible','v778-menu-grid','Inicio','Picks'],
    'account_center.html':['Mi cuenta','Telegram','Membresía','v778-section-grid'],
    'calendar.html':['match_madrid_context','client_full_datetime_label'],
    'live.html':['match_full_datetime','Hora Madrid'],
    'picks.html':['match_full_datetime','client_full_datetime_label'],
    'combis.html':['madrid_datetime_label'],
    'activity.html':['madrid_datetime_label'],
    'alerts.html':['madrid_datetime_label'],
}
for name,tokens in required_templates.items():
    raw=(ROOT/'templates'/name).read_text(encoding='utf-8')
    for token in tokens:
        if token not in raw:
            errors.append(f'{name} no contiene {token}')
    if 'v775-page-shortcuts' in raw and name in {'calendar.html','live.html','picks.html'}:
        errors.append(f'{name} conserva shortcuts duplicados V775')
for name in ['client_app_center.html','client_menu.html','account_center.html']:
    raw=(ROOT/'templates'/name).read_text(encoding='utf-8').lower()
    bad=[t for t in [' utc','debug','traceback','json visible'] if t in raw]
    if bad:
        errors.append(f'{name} contiene texto técnico visible: {bad}')
if errors:
    print('\n'.join('ERROR: '+e for e in errors))
    sys.exit(1)
print('OK V778 client product organization + Madrid time final stability')
