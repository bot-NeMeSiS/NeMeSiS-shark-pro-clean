from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(cond, msg):
    if not cond:
        raise SystemExit(f"FAIL: {msg}")

version = (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
app = (ROOT/'app.py').read_text(encoding='utf-8')
css = (ROOT/'static/app.css').read_text(encoding='utf-8')
require(version in ['V793_CLIENT_PIXEL_MATCH_SCREEN_REBUILD','V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM','V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH','V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH'], f'VERSION inesperada: {version}')
require(('APP_VERSION = "V793_CLIENT_PIXEL_MATCH_SCREEN_REBUILD"' in app) or ("APP_VERSION = 'V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM'" in app) or ('APP_VERSION = "V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM"' in app) or ("APP_VERSION = 'V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH'" in app) or ("APP_VERSION = 'V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH'" in app), 'APP_VERSION no actualizado')
require('data-v793-shell="true"' in (ROOT/'templates/base.html').read_text(encoding='utf-8'), 'base sin shell V793')
need_css = ['v793-home-hero','v793-live-feature','v793-agenda-row','v793-pick-feature','v793-match-hero','v793-plan-card','v793-profile-card','v793-telegram-status','v793-track-screen']
for token in need_css:
    require(token in css, f'CSS V793 falta {token}')
checks = {
 'templates/client_app_center.html':['Buenos días','Ruta recomendada de hoy','Pick destacado','v793-home-grid'],
 'templates/live.html':['v793-live-feature','v793-scoreboard','v793-live-grid'],
 'templates/calendar.html':['Agenda ordenada','v793-agenda-row','v793-league-block'],
 'templates/picks.html':['Pick destacado','Por qué entrar','Riesgos','v793-pick-feature'],
 'templates/match_detail.html':['Resumen SHARK','Pick recomendado','Forma reciente','v793-match-hero'],
 'templates/membership.html':['Elige tu plan','No garantizamos beneficios','v793-plan-grid'],
 'templates/account_center.html':['Mi cuenta','Plan actual','Telegram conectado','v793-profile-card'],
 'templates/telegram.html':['Lo que recibirás en tu canal','Conecta Telegram','Código de vinculación'],
 'templates/track_record.html':['Histórico','ROI real','Solo resultados reales']
}
for rel,tokens in checks.items():
    txt=(ROOT/rel).read_text(encoding='utf-8')
    for token in tokens:
        require(token in txt, f'{rel} falta {token}')
print('OK V793 client pixel-match rebuild')
