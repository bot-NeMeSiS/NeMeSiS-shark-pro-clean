#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V800_REFERENCE_SCREEN_APP_FIDELITY_REAL_DATA_NAVIGATION_FINAL'

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def require(cond, msg):
    if not cond:
        raise SystemExit(f'FAIL: {msg}')

version = (ROOT / 'VERSION.txt').read_text(encoding='utf-8-sig').strip()
app = read('app.py')
base = read('templates/base.html')
css = read('static/app.css')

require(version == VERSION, f'VERSION inesperada: {version}')
require(f"APP_VERSION = '{VERSION}'" in app, 'APP_VERSION no coincide con VERSION.txt')

for token in ['data-v800-shell="true"', 'v800-rail-status', 'v800ClientFidelity', '/logout', 'Cerrar sesión']:
    require(token in base, f'base.html sin {token}')

expected = {
    'templates/home.html': ['v800-stage', 'v800-feature-match', 'Esperando calendario real', 'No se inventa una oportunidad'],
    'templates/client_app_center.html': ['v800-app-stage', 'Partido recomendado para abrir', 'Partido → Pick → SHARK'],
    'templates/calendar.html': ['v800-command-row', 'v800-row-ribbon', 'Pick publicado', 'Analizar partido'],
    'templates/live.html': ['v800-live-ticker', 'Sin directos reales ahora', 'live_score_label'],
    'templates/picks.html': ['v800-pick-command', 'v800-decision-grid', 'Qué apostar', 'Riesgo pendiente'],
    'templates/match_detail.html': ['v800-match-strip', 'v800-side-cta', 'Preguntar por este partido'],
    'templates/account_center.html': ['v800-account-safe', 'Cerrar sesión'],
    'templates/telegram.html': ['v800-telegram-flow', 'Vincula el bot', 'Recibe alertas reales'],
}
for rel, tokens in expected.items():
    text = read(rel)
    for token in tokens:
        require(token in text, f'{rel} sin {token}')

for token in [VERSION, 'data-v800-shell', '.v800-stage', '.v800-command-row', '.v800-live-ticker', '.v800-match-strip']:
    require(token in css or token in base or token in app, f'capa V800 sin {token}')

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

for token in ['DB_PATH', 'AUTOMATION_SECRET', '/api/automation/telegram/tick', 'record_user_activity("view", "match"']:
    require(token in app, f'app.py perdió referencia crítica {token}')

print('V800 reference screen app fidelity + real-data navigation check OK')
