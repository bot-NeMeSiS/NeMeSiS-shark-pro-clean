#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V798_REFERENCE_VISUAL_CLIENT_FLOW_REAL_DATA_FINAL'

def require(cond, msg):
    if not cond:
        raise SystemExit(f'FAIL: {msg}')

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

version = (ROOT / 'VERSION.txt').read_text(encoding='utf-8-sig').strip()
app = read('app.py')
base = read('templates/base.html')
css = read('static/app.css')

require(version == VERSION, f'VERSION inesperada: {version}')
require(f"APP_VERSION = '{VERSION}'" in app, 'APP_VERSION no actualizado a V798')

for token in ['data-v798-shell="true"', 'v798-brand', 'v798-shark-mark', 'v798-client-rail']:
    require(token in base, f'base.html sin {token}')

expected_templates = {
    'templates/client_app_center.html': ['v798-dashboard', 'v798-hero', 'v798-quick-row', 'Datos reales'],
    'templates/calendar.html': ['v798-hero-shark', 'v798-agenda-card', 'Ver previa', 'Análisis SHARK'],
    'templates/live.html': ['v798-live-feature', 'v798-live-grid', 'Ver partido'],
    'templates/picks.html': ['v798-pick-feature', 'v798-pick-grid', 'Qué apostar'],
    'templates/match_detail.html': ['v798-match-hero', 'v798-match-meta-grid', 'Datos reales del partido'],
    'templates/account_center.html': ['v798-account-screen', 'Cerrar sesión', 'Actividad reciente'],
    'templates/telegram.html': ['v798-telegram-screen', 'Código de vinculación', 'Conecta Telegram'],
}
for rel, tokens in expected_templates.items():
    text = read(rel)
    for token in tokens:
        require(token in text, f'{rel} sin {token}')

for token in [VERSION, 'body[data-v798-shell="true"]', '.v798-client-rail', '.v798-agenda-card', '.v798-pick-feature']:
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

print('V798 reference visual client flow + real-data check OK')
