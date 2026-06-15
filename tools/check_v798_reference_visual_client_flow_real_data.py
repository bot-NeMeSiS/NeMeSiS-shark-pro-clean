#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PREFIXES = (
    'V798_REFERENCE_VISUAL_CLIENT_FLOW_REAL_DATA_FINAL',
    'V799_REFERENCE_SCREEN_VISUAL_POLISH_APP_LIKE_FINAL',
    'V800_REFERENCE_SCREEN_APP_FIDELITY_REAL_DATA_NAVIGATION_FINAL',
)

def require(cond, msg):
    if not cond:
        raise SystemExit(f'FAIL: {msg}')

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

version = (ROOT / 'VERSION.txt').read_text(encoding='utf-8-sig').strip()
app = read('app.py')
base = read('templates/base.html')
css = read('static/app.css')
require(version in ALLOWED_PREFIXES, f'VERSION inesperada: {version}')
require(f"APP_VERSION = '{version}'" in app, 'APP_VERSION no coincide con VERSION.txt')

for token in ['data-v798-shell="true"', 'v798-brand', 'v798-shark-mark', 'v798-client-rail']:
    require(token in base, f'base.html sin {token}')

expected_templates = {
    'templates/client_app_center.html': ['Datos reales' if version.startswith('V798') else 'v799-dashboard-grid', 'SHARK'],
    'templates/calendar.html': ['Análisis SHARK' if version.startswith('V798') else 'v799-agenda-row', 'SHARK'],
    'templates/live.html': ['Ver partido' if version.startswith('V798') else 'Abrir partido'],
    'templates/picks.html': ['Qué apostar' if version.startswith('V798') else 'v799-feature-pick', 'SHARK'],
    'templates/match_detail.html': ['Datos reales' if version.startswith('V798') else 'v799-real-data-grid'],
    'templates/account_center.html': ['Cerrar sesión'],
    'templates/telegram.html': ['Código de vinculación' if version.startswith('V798') else 'v799-code', 'Telegram'],
}
for rel, tokens in expected_templates.items():
    text = read(rel)
    for token in tokens:
        require(token in text, f'{rel} sin {token}')

for token in ['body[data-v798-shell="true"]', '.v798-client-rail']:
    require(token in css, f'static/app.css sin {token}')

fake_tokens = [
    '98.72%', '1.237', '812', '65.7%', 'Hoy traemos 3 selecciones',
    'Pick generado', 'Alerta enviada', 'G E G P G', 'G P E G P', '+6.3', '72%', '63%'
]
scan_paths = [
    'templates/client_app_center.html', 'templates/calendar.html', 'templates/live.html', 'templates/picks.html',
    'templates/match_detail.html', 'templates/account_center.html', 'templates/telegram.html',
    'templates/admin_telegram_command_center.html'
]
for rel in scan_paths:
    text = read(rel)
    for token in fake_tokens:
        require(token not in text, f'{rel} conserva dato/ejemplo ficticio visible: {token}')

for token in ['record_user_activity("view", "match"', 'detail["client_premium"]']:
    require(token in app, f'app.py sin integración segura {token}')

print('V798/V799/V800 reference visual client flow + real-data check OK')
