#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]

def fail(msg: str):
    print('FAIL:', msg)
    sys.exit(1)

def require(cond, msg: str):
    if not cond:
        fail(msg)

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8', errors='ignore')

version = read('VERSION.txt').strip()
app = read('app.py')
base = read('templates/base.html')
css = read('static/app.css')
continuation = read('CHATGPT_CONTINUATION_REPORT.md')

require(version.startswith('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH') or version.startswith('V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL') or version.startswith('V792_CLIENT_MOCKUP_VISUAL_SYSTEM_IMPLEMENTATION') or version.startswith('V793_CLIENT_PIXEL_MATCH_SCREEN_REBUILD') or version.startswith('V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM') or version.startswith('V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH') or version.startswith('V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH'), f'VERSION inesperada: {version}')
require('APP_VERSION' in app and ('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH' in app or 'V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL' in app or 'V792_CLIENT_MOCKUP_VISUAL_SYSTEM_IMPLEMENTATION' in app or 'V793_CLIENT_PIXEL_MATCH_SCREEN_REBUILD' in app or 'V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM' in app or 'V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH' in app or 'V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH' in app), 'APP_VERSION no actualizado')
require('data-v790-shell="true"' in base, 'base.html sin bandera visual V790')
for token in [
    'V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH',
    '--v790-surface',
    'body.ns-authenticated:not(.ns-admin)[data-v790-shell="true"]',
    '.v774-client-hero',
    '.v774-filter-form',
    'data-ns-route^="/live"',
    'data-ns-route^="/calendar"',
    '.v774-match-card',
    '.v774-teams',
    '.v774-pick-card',
    '.v785-price-card',
    '.v775-telegram-code',
    '@media(max-width:760px)',
]:
    require(token in css, f'CSS V790 incompleto: {token}')

client_template_markers = {
    'templates/live.html': [['v774-card-grid', 'v774-match-card', 'v774-teams'], ['v793-live-grid', 'v793-live-card', 'v793-scoreboard']],
    'templates/calendar.html': [['v774-day-stack', 'v774-league-block', 'v774-match-card'], ['v793-agenda', 'v793-agenda-row', 'v793-league-block']],
    'templates/picks.html': [['v774-pick-card', 'v774-pick-main', 'Lectura SHARK'], ['v793-pick-feature', 'v793-pick-card', 'Por qué entrar']],
    'templates/membership.html': [['v785-price-card', 'v787-checkout-legal', 'Pagar PRO'], ['v793-plan-card', 'v793-legal-checks', 'Elegir PRO']],
    'templates/account_center.html': [['Mi cuenta', 'Telegram', 'Membresía'], ['Mi cuenta', 'Telegram conectado', 'Plan actual']],
    'templates/telegram.html': [['Telegram conectado', 'Código de vinculación', 'Qué recibirás'], ['Lo que recibirás en tu canal', 'Código de vinculación', 'Conecta Telegram']],
}
for rel, marker_sets in client_template_markers.items():
    text = read(rel)
    require(any(all(token in text for token in marker_set) for marker_set in marker_sets), f'{rel} sin estructura cliente clave compatible V790+')

require(('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH' in continuation) or ('V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH' in continuation), 'continuation report sin V790/V796')
print('OK V790 client professional screen system total polish')
