#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
errors=[]
version=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
if 'V792_CLIENT_MOCKUP_VISUAL_SYSTEM_IMPLEMENTATION' not in version:
    errors.append('VERSION.txt no contiene V792')
base=(ROOT/'templates'/'base.html').read_text(encoding='utf-8')
for token in ['data-v792-shell="true"','Partidos</a>','/mi-cuenta" data-v775-icon="◎">Cuenta']:
    if token not in base:
        errors.append(f'base.html falta {token}')
css=(ROOT/'static'/'app.css').read_text(encoding='utf-8')
for token in ['V792_CLIENT_MOCKUP_VISUAL_SYSTEM_IMPLEMENTATION','.v792-home-command','data-ns-route^="/live"','data-ns-route^="/calendar"','data-ns-route^="/picks"','data-ns-route^="/match/"']:
    if token not in css:
        errors.append(f'app.css falta {token}')
home=(ROOT/'templates'/'home.html').read_text(encoding='utf-8')
for token in ['v792-home-command','Buenos días','Ruta recomendada de hoy','Partidos destacados','Pick destacado','v792-quick-access']:
    if token not in home:
        errors.append(f'home.html falta {token}')
for tpl, words in {
    'live.html':['<h1>Directo</h1>','Partidos en juego ahora'],
    'calendar.html':['<h1>Partidos</h1>','Agenda ordenada por día y competición'],
    'picks.html':['<h1>Picks SHARK</h1>','Selecciones recomendadas del día'],
    'track_record.html':['<h1>Histórico</h1>','Resultados reales y rendimiento'],
    'membership.html':['<h1>Elige tu plan</h1>','Accede a análisis, alertas y funciones premium'],
}.items():
    text=(ROOT/'templates'/tpl).read_text(encoding='utf-8')
    for word in words:
        if word not in text:
            errors.append(f'{tpl} falta {word}')
if errors:
    print('V792 CHECK FAILED')
    for e in errors: print('-', e)
    raise SystemExit(1)
print('V792 CHECK OK')
