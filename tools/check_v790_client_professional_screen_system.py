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

require(version.startswith('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH'), f'VERSION inesperada: {version}')
require('APP_VERSION = "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH"' in app, 'APP_VERSION no actualizado')
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

for rel, tokens in {
    'templates/live.html': ['v774-card-grid', 'v774-match-card', 'v774-teams', 'Actualizar directo'],
    'templates/calendar.html': ['v774-day-stack', 'v774-league-block', 'v774-match-card', 'Hora Madrid'],
    'templates/picks.html': ['v774-pick-card', 'v774-pick-main', 'Lectura SHARK'],
    'templates/membership.html': ['v785-price-card', 'v787-checkout-legal', 'Pagar PRO', 'Pagar ELITE'],
    'templates/account_center.html': ['Mi cuenta', 'Telegram', 'Membresía'],
    'templates/telegram.html': ['Telegram conectado', 'Código de vinculación', 'Qué recibirás'],
}.items():
    text = read(rel)
    for token in tokens:
        require(token in text, f'{rel} sin estructura cliente clave: {token}')

require('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH' in continuation, 'continuation report sin V790')
print('OK V790 client professional screen system total polish')
