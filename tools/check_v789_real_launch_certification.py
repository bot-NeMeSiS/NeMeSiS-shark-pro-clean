#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]

def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)

def require(cond, msg):
    if not cond:
        fail(msg)

def read(rel):
    return (ROOT/rel).read_text(encoding='utf-8', errors='ignore')

version = read('VERSION.txt').strip()
app = read('app.py')
engine = read('engines/real_launch_engine.py')
template = read('templates/admin_real_launch.html')
css = read('static/app.css')
report = read('reports/V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER_REPORT.md')
continuation = read('CHATGPT_CONTINUATION_REPORT.md')

require(version.startswith('V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER') or version.startswith('V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH') or version.startswith('V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL') or version.startswith('V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL'), f'VERSION inesperada: {version}')
require('APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app, 'APP_VERSION no actualizado')
for token in ['real_launch_snapshot', '/admin/real-launch', '/api/admin/real-launch', 'admin_real_launch.html']:
    require(token in app, f'app.py sin {token}')
for token in ['REAL_LAUNCH_VERSION', 'RISKY_COPY_TERMS', 'STRIPE_ACCOUNT_VERIFIED', 'LEGAL_REVIEW_COMPLETED', 'safe_business_description', 'NO PASAR A LIVE TODAVÍA']:
    require(token in engine, f'engine real launch incompleto: {token}')
for token in ['Real Launch Command Center', 'Stripe real', 'Legal y responsabilidad', 'Render y seguridad', 'Copys peligrosos detectados', 'Descripción segura del negocio']:
    require(token in template, f'template real launch incompleto: {token}')
for token in ['V789 real launch certification command center', '.v789-launch-score', '.v789-db-grid']:
    require(token in css, f'CSS V789 ausente: {token}')
for token in ['STRIPE_ACCOUNT_VERIFIED=false', 'LEGAL_OWNER_DETAILS_COMPLETED=false', 'LEGAL_REVIEW_COMPLETED=false']:
    require(token in read('.env.example'), f'.env.example sin {token}')
    require(token in read('.env.render.clean'), f'.env.render.clean sin {token}')
require('V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER' in report, 'reporte V789 incompleto')
require('V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER' in continuation, 'continuation report sin V789')
print('OK V789 real launch certification command center')
