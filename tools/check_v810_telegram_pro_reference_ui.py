#!/usr/bin/env python3
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]

def ok(cond,msg):
    if not cond:
        raise SystemExit(f"FAIL: {msg}")

version=(ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip()
ok(version.startswith('V810_') or version.startswith('V811_'), 'VERSION no es V810/V811')
base=(ROOT/'templates/base.html').read_text(encoding='utf-8')
css=(ROOT/'static/app.css').read_text(encoding='utf-8')
activity=(ROOT/'engines/telegram_activity_engine.py').read_text(encoding='utf-8')
formatter=(ROOT/'engines/telegram_message_formatter.py').read_text(encoding='utf-8')
app=(ROOT/'app.py').read_text(encoding='utf-8')
ok('data-v810-shell="true"' in base, 'base no activa V810')
ok('v810-big-shark-decoration' in base and 'v810-big-shark-decoration' in css, 'falta tiburon decorativo')
ok(base.count('class="shark-widget"') == 1, 'debe existir un unico shark-widget en base')
ok('v810SingleSharkButton' in base, 'falta dedupe de boton SHARK')
ok('/shark?team=' in (ROOT/'templates/team_detail.html').read_text(encoding='utf-8'), 'enlace SHARK equipo no corregido')
ok('TELEGRAM_PROFESSIONAL_COMPETITIONS_ONLY' in activity, 'falta filtro profesional Telegram')
ok('filter_telegram_professional_items' in activity, 'falta funcion filtro items Telegram')
ok('competicion_no_top_para_canal_telegram' in activity, 'falta motivo descarte ligas no top')
ok('Agenda TOP del dÃ­a' in formatter and 'PICK SHARK PRO' in formatter and 'LIVE SHARK' in formatter, 'formatos Telegram PRO no aplicados')
ok('/admin/telegram/pro-preview' in app, 'falta ruta preview Telegram PRO')
ok((ROOT/'templates/admin_telegram_pro_preview.html').exists(), 'falta template preview Telegram PRO')
for env in ['.env.example','.env.render.clean']:
    text=(ROOT/env).read_text(encoding='utf-8')
    ok('TELEGRAM_PROFESSIONAL_COMPETITIONS_ONLY=true' in text, f'falta env profesional en {env}')
# links malformed like /sharkteam= or /apix= without ?
bad=[]
for p in (ROOT/'templates').rglob('*.html'):
    text=p.read_text(encoding='utf-8', errors='ignore')
    for href in re.findall(r'href=["\']([^"\']*=[^"\']*)["\']', text):
        if '?' not in href and not href.startswith(('http','mailto','#')):
            bad.append((str(p.relative_to(ROOT)), href))
ok(not bad, 'href malformados: '+repr(bad[:10]))
print('V810 Telegram PRO + reference UI check OK')


