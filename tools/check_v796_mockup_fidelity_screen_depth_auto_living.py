#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(cond, msg):
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
version = (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
app = (ROOT/'app.py').read_text(encoding='utf-8')
base = (ROOT/'templates/base.html').read_text(encoding='utf-8')
admin = (ROOT/'templates/partials/admin_visual_system.html').read_text(encoding='utf-8')
css = (ROOT/'static/app.css').read_text(encoding='utf-8')
require(version in ['V793_CLIENT_PIXEL_MATCH_SCREEN_REBUILD','V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM','V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH','V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH','V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH'], f'VERSION inesperada: {version}')
require("APP_VERSION = 'V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH'" in app or 'APP_VERSION = \"V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH\"' in app, 'APP_VERSION no actualizado')
for token in ['data-v796-shell="true"', 'function v796RuntimeHeartbeat', 'data-v796-runtime']:
    require(token in base, f'base falta {token}')
for token in ['v796-admin-shell', 'v796-runtime-pill', 'v796-command-ribbon', 'Fidelidad mockup V796']:
    require(token in admin, f'admin partial falta {token}')
for token in ['V796_MOCKUP_FIDELITY', 'body.ns-admin[data-v796-shell="true"]', 'body.ns-authenticated:not(.ns-admin)[data-v796-shell="true"]', 'v796Enter', 'v796-runtime-pill']:
    require(token in css, f'CSS falta {token}')
# Ensure critical pages still use the rebuilt systems
pages = {
 'templates/client_app_center.html':['v793-home-grid','Ruta recomendada de hoy'],
 'templates/live.html':['v793-live-feature','v793-scoreboard'],
 'templates/calendar.html':['v793-agenda-row','Agenda ordenada'],
 'templates/picks.html':['v793-pick-feature','Por qué entrar'],
 'templates/match_detail.html':['v793-match-hero','Resumen SHARK'],
 'templates/admin_dashboard.html':['ui.shell','Panel de control'],
 'templates/admin_telegram_command_center.html':['ui.shell','Telegram Command Center'],
 'templates/admin_payments.html':['ui.shell','Pagos y membresías'],
 'templates/admin_automation_center.html':['ui.shell','Centro de automatización'],
 'templates/admin_data_marketplace.html':['ui.shell','Data Marketplace'],
 'templates/admin_real_launch.html':['ui.shell','Lanzamiento real'],
 'templates/admin_client_screen_audit.html':['ui.shell','Auditoría cliente'],
 'templates/admin_picks.html':['ui.shell','Picks y partidos'],
}
for rel, toks in pages.items():
    text=(ROOT/rel).read_text(encoding='utf-8')
    for tok in toks:
        require(tok in text, f'{rel} falta {tok}')
print('check_v796_mockup_fidelity_screen_depth_auto_living OK')
