#!/usr/bin/env python3
from pathlib import Path
import re, sys
ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()
errors=[]
def read(rel):
    p=ROOT/rel
    if not p.exists():
        errors.append(f'missing {rel}')
        return ''
    return p.read_text(encoding='utf-8')
app=read('app.py')
base=read('templates/base.html')
client=read('templates/client_app_center.html')
menu=read('templates/client_menu.html')
css=read('static/app.css')
if not (VERSION.startswith('V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER') or VERSION.startswith('V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM') or VERSION.startswith('V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY')):
    errors.append(f'bad VERSION {VERSION}')
if 'APP_VERSION = "V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER"' not in app and 'APP_VERSION = "V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM"' not in app and 'APP_VERSION = "V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY"' not in app:
    errors.append('APP_VERSION not updated')
for token in ['/calendar?lane=today','/highlights','/telegram','/menu']:
    if token not in base:
        errors.append(f'base missing {token}')
for token in ['Centro de mando','Ruta recomendada','/track-record','/mi-cuenta']:
    if token not in client:
        errors.append(f'client app missing {token}')
for token in ['Mapa final','/mapa','nada escondido']:
    if token not in menu and token not in app:
        errors.append(f'menu/app missing {token}')
for token in ['@app.route("/mapa")','@app.route("/navegacion")','def v776_client_information_architecture_snapshot']:
    if token not in app:
        errors.append(f'app missing {token}')
if 'V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER' not in css and 'V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM' not in css and 'V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY' not in css:
    errors.append('css V776 block missing')
if 'Todo lo secundario' in menu or 'El resto queda en Más' in client or 'queda en Más' in client:
    errors.append('bad hidden/secondary copy remains in key client screens')
if errors:
    print('check_v776_client_information_architecture')
    for e in errors: print('ERROR:', e)
    sys.exit(1)
print('check_v776_client_information_architecture')
print('OK - V776 visible client information architecture validated')
