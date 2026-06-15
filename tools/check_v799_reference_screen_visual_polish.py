#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ALLOWED_VERSIONS = {'V799_REFERENCE_SCREEN_VISUAL_POLISH_APP_LIKE_FINAL', 'V800_REFERENCE_SCREEN_APP_FIDELITY_REAL_DATA_NAVIGATION_FINAL'}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def require(cond, msg):
    if not cond:
        raise SystemExit(f'FAIL: {msg}')

version = (ROOT / 'VERSION.txt').read_text(encoding='utf-8-sig').strip()
app = read('app.py')
base = read('templates/base.html')
css = read('static/app.css')

require(version in ALLOWED_VERSIONS, f'VERSION inesperada: {version}')
require(f"APP_VERSION = '{version}'" in app, 'APP_VERSION no coincide con VERSION.txt')

for token in ['data-v799-shell="true"', 'v799-client-rail', 'v799-rail-brand', 'v799-rail-logout', '/logout', 'Cerrar sesión']:
    require(token in base, f'base.html sin {token}')

expected = {
    'templates/client_app_center.html': ['v799-app-center-screen', 'v799-dashboard-grid', 'v799-mobile-preview', 'Partidos de hoy'],
    'templates/home.html': ['v799-home-screen', 'v799-dashboard-grid', 'v799-mobile-preview', 'No se mostrará ninguna oportunidad'],
    'templates/calendar.html': ['v799-calendar-screen', 'v799-calendar-layout', 'v799-agenda-row', 'SHARK'],
    'templates/live.html': ['v799-live-screen', 'v799-scoreboard', 'No hay partidos en directo ahora mismo', 'Abrir partido'],
    'templates/picks.html': ['v799-picks-screen', 'v799-feature-pick', 'v799-reason-grid', 'No hay picks activos ahora mismo'],
    'templates/match_detail.html': ['v799-match-screen', 'v799-match-hero', 'v799-real-data-grid', 'Sin pick publicado'],
    'templates/account_center.html': ['v799-account-screen', 'Cerrar sesión', 'v799-profile-hero', 'v799-action-stack'],
    'templates/telegram.html': ['v799-telegram-screen', 'v799-code', 'Conectar Telegram', 'v799-benefits-grid'],
}
for rel, tokens in expected.items():
    text = read(rel)
    for token in tokens:
        require(token in text, f'{rel} sin {token}')

for token in ['body.ns-authenticated:not(.ns-admin)[data-v799-shell="true"]', '.v799-dashboard-grid', '.v799-mobile-preview', '.v799-client-rail']:
    require(token in css, f'static/app.css sin {token}')

fake_tokens = [
    '98.72%', '1.237', '812', '65.7%', 'Hoy traemos 3 selecciones',
    'Pick generado', 'Alerta enviada', 'G E G P G', 'G P E G P', '+6.3',
    'Condiciones favorables según SHARK', 'Pick publicado con control de riesgo'
]
scan_paths = list(expected.keys()) + ['templates/admin_telegram_command_center.html']
for rel in scan_paths:
    text = read(rel)
    for token in fake_tokens:
        require(token not in text, f'{rel} conserva dato/ejemplo ficticio visible: {token}')

# V799 must keep route integration and avoid touching critical production paths.
for token in ['@app.route("/app")', '@app.route("/calendar")', '@app.route("/live")', '@app.route("/picks")', '@app.route("/mi-cuenta")']:
    require(token in app, f'app.py sin ruta esperada {token}')
for token in ['DB_PATH', 'AUTOMATION_SECRET', '/api/automation/telegram/tick']:
    require(token in app, f'app.py perdió referencia crítica {token}')

print('V799/V800 reference screen visual polish + real-data check OK')
