#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(cond, msg):
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
version = (ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()
app = (ROOT/'app.py').read_text(encoding='utf-8')
base = (ROOT/'templates/base.html').read_text(encoding='utf-8')
css = (ROOT/'static/app.css').read_text(encoding='utf-8')
admin = (ROOT/'templates/partials/admin_visual_system.html').read_text(encoding='utf-8')
account = (ROOT/'templates/account_center.html').read_text(encoding='utf-8')
require(version == 'V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH', f'VERSION inesperada: {version}')
require("APP_VERSION = 'V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH'" in app, 'APP_VERSION no actualizado')
for token in ['data-v797-shell="true"', 'v797-session-pills', 'v797-nav-logout']:
    require(token in base, f'base sin {token}')
for token in ['Cerrar sesión', '/logout', 'v797-admin-logout']:
    require(token in admin or token in account or token in base, f'falta salida {token}')
for token in ['V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH', 'v797-truth-empty', 'Datos reales · sin ejemplos ficticios']:
    require(token in css, f'CSS sin {token}')
for path in ['templates/admin_payments.html','templates/admin_telegram_command_center.html','templates/admin_dashboard.html']:
    text = (ROOT/path).read_text(encoding='utf-8')
    require('2.458' not in text and '48.732' not in text and '18.732' not in text, f'{path} conserva datos mock visibles')
print('V797 render visual QA/logout/real data check OK')
