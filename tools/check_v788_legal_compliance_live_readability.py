#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()

def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)

def require(cond, msg):
    if not cond:
        fail(msg)

def read(rel):
    return (ROOT/rel).read_text(encoding='utf-8', errors='ignore')

app = read('app.py')
css = read('static/app.css')
live = read('templates/live.html')
membership = read('templates/membership.html')
legal_engine = read('engines/legal_compliance_engine.py')
continuation = read('CHATGPT_CONTINUATION_REPORT.md')

require(VERSION.startswith('V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH') or VERSION.startswith('V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER') or VERSION.startswith('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH'), f'VERSION inesperada: {VERSION}')
require('APP_VERSION = "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH"' in app, 'APP_VERSION no actualizado')
for token in ['enforce_checkout_legal_gate', 'user_legal_acceptances', 'record_legal_checkout_acceptance', '/no-somos-casa-de-apuestas']:
    require(token in app, f'protección legal ausente: {token}')
for token in ['LEGAL_COMPLIANCE_VERSION = "V788-LEGAL-2026-06-14"', 'accept_not_betting_operator', 'accept_no_guarantee']:
    require(token in legal_engine, f'engine legal V788 incompleto: {token}')
for token in ['v787-checkout-legal', 'required', 'No compra apuestas, premios ni resultados garantizados', 'Continuar a Stripe']:
    require(token in membership, f'membership legal/pago incompleto: {token}')
for token in ['V788 legal compliance + live readability total polish', 'body.ns-authenticated:not(.ns-admin)', '.v774-match-card', '.v774-teams strong', '.v774-league-block', 'font-size:16.5px', 'grid-template-columns:repeat(auto-fit,minmax(360px,1fr))']:
    require(token in css, f'CSS V788 legibilidad/directo ausente: {token}')
for token in ['v774-card-grid', 'v774-match-card', 'v774-teams', 'Hora Madrid']:
    require(token in live, f'live.html estructura clave ausente: {token}')
require('V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH' in continuation, 'continuation report no actualizado con V788')
print('OK V788 legal compliance + live readability total polish')
