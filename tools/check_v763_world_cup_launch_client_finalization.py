#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION="V763_WORLD_CUP_LAUNCH_CLIENT_FINALIZATION_POLISH"
def ok(c,m):
    if not c: raise SystemExit(f"[V763][FAIL] {m}")
    print(f"[V763][OK] {m}")
version=(ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()
ok(version==VERSION,'VERSION.txt apunta a V763')
app=(ROOT/'app.py').read_text(encoding='utf-8')
ok(f'APP_VERSION = "{VERSION}"' in app,'APP_VERSION V763')
ok('build_v763_world_cup_launch_context' in app and '@app.route("/mundial")' in app,'modo Mundial registrado')
ok('/api/client/world-cup-snapshot' in app,'API snapshot Mundial registrada')
ok('tools/render_cron_telegram_tick.py' not in app or '/api/automation/telegram/tick' in app,'Cron/Telegram conservado')
base=(ROOT/'templates/base.html').read_text(encoding='utf-8')
ok('/mundial' in base and 'Mundial' in base,'navegación cliente incluye Mundial')
ok(base.count("thinking.textContent=answer; thinking.classList.remove('thinking');") == 1,'SHARK JS sin línea duplicada')
home=(ROOT/'templates/home.html').read_text(encoding='utf-8')
ok('v763-world-cup-band' in home and '/mundial' in home,'home muestra bloque modo Mundial')
ok((ROOT/'templates/world_cup_launch.html').exists(),'template modo Mundial existe')
menu=app
ok('Modo Mundial' in menu and 'v566_client_menu_items' in menu,'menú cliente tiene Modo Mundial')
css=(ROOT/'static/app.css').read_text(encoding='utf-8')
ok('V763_WORLD_CUP_LAUNCH_CLIENT_FINALIZATION_POLISH' in css,'CSS V763 aplicado')
for name in ['V763_WORLD_CUP_LAUNCH_CLIENT_FINALIZATION_POLISH_REPORT.md','V763_FINAL_LAUNCH_QA_CHECKLIST.md']:
    ok((ROOT/'reports'/name).exists(),f'reporte {name} existe')
print('[V763] checks OK')
