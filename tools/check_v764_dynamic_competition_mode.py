#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION="V764_DYNAMIC_COMPETITION_MODE_ENGINE"
NEXT_VERSIONS={"V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH"}
def ok(c,m):
    if not c:
        raise SystemExit(f"[V764][FAIL] {m}")
    print(f"[V764][OK] {m}")
version=(ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()
ok(version==VERSION or version in NEXT_VERSIONS,'VERSION.txt apunta a V764 o versión posterior compatible')
app=(ROOT/'app.py').read_text(encoding='utf-8')
ok(f'APP_VERSION = "{VERSION}"' in app or any(f'APP_VERSION = "{v}"' in app for v in NEXT_VERSIONS),'APP_VERSION V764 o posterior compatible')
ok('build_v764_dynamic_competition_mode' in app,'motor dinámico creado')
ok('@app.route("/modo-dinamico")' in app and '/api/client/dynamic-mode' in app,'rutas/API modo dinámico registradas')
ok('tools/render_cron_telegram_tick.py' not in app or '/api/automation/telegram/tick' in app,'Cron/Telegram conservado')
ok('AUTOMATION_SECRET' in app and 'DB_PATH' in app,'secret/DB_PATH siguen presentes')
for tpl in ['home.html','calendar.html','live.html','picks.html','world_cup_launch.html','dynamic_mode.html','base.html']:
    p=ROOT/'templates'/tpl
    ok(p.exists(),f'{tpl} existe')
    txt=p.read_text(encoding='utf-8')
    if tpl in {'home.html','calendar.html','live.html','picks.html','world_cup_launch.html'}:
        ok('dynamic_mode' in txt or 'v764-auto-mode' in txt, f'{tpl} incluye modo automático')
base=(ROOT/'templates/base.html').read_text(encoding='utf-8')
ok('/modo-dinamico' in base and 'Momento' in base,'navegación cliente tiene Momento')
css=(ROOT/'static/app.css').read_text(encoding='utf-8')
ok('V764_DYNAMIC_COMPETITION_MODE_ENGINE' in css,'CSS V764 aplicado')
menu=app
ok('Modo automático' in menu and '/modo-dinamico' in menu,'menú cliente incluye modo automático')
for name in ['V764_DYNAMIC_COMPETITION_MODE_ENGINE_REPORT.md','V764_DYNAMIC_MODE_CLIENT_QA_CHECKLIST.md','V764_NEXT_STEPS_SALE_READY.md']:
    ok((ROOT/'reports'/name).exists(),f'reporte {name} existe')
print('[V764] checks OK')
