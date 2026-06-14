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
if not VERSION.startswith('V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER'):
    errors.append(f'bad VERSION {VERSION}')
if 'APP_VERSION = "V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER"' not in app:
    errors.append('APP_VERSION not updated')
for token in ['v776-client-compass','/calendar?lane=today','/combis','/mercados','/highlights','/telegram','/menu']:
    if token not in base:
        errors.append(f'base missing {token}')
for token in ['v776-visible-map','Todo lo que tiene la app','/modo-dinamico','/mundial','/perfil','/ayuda']:
    if token not in client:
        errors.append(f'client app missing {token}')
for token in ['Mapa completo','groupby(\'group\')','/mapa','nada escondido']:
    if token not in menu and token not in app:
        errors.append(f'menu/app missing {token}')
for token in ['@app.route("/mapa")','@app.route("/navegacion")','def v776_client_information_architecture_snapshot']:
    if token not in app:
        errors.append(f'app missing {token}')
if 'V776_CLIENT_INFORMATION_ARCHITECTURE_FINAL_ORDER' not in css:
    errors.append('css V776 block missing')
if 'Todo lo secundario' in menu or 'El resto queda en Más' in client or 'queda en Más' in client:
    errors.append('bad hidden/secondary copy remains in key client screens')
if errors:
    print('check_v776_client_information_architecture')
    for e in errors: print('ERROR:', e)
    sys.exit(1)
print('check_v776_client_information_architecture')
print('OK - V776 visible client information architecture validated')
