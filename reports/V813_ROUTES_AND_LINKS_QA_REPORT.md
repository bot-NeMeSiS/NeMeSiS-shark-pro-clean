# V813 Routes and Links QA Report

## Rutas cliente verificadas por check

- `/`
- `/app`
- `/sports-hub`
- `/calendar`
- `/partidos`
- `/live`
- `/directo`
- `/match/<id>`
- `/team/<id>`
- `/picks`
- `/combis`
- `/favorites`
- `/telegram`
- `/shark`
- `/profile`
- `/perfil`
- `/mi-cuenta`
- `/soporte`
- `/support`

## Rutas admin verificadas por check

- `/admin/dashboard`
- `/admin/control-center`
- `/admin/map`
- `/admin/data-center`
- `/admin/automation-center`
- `/admin/telegram/diagnostics`

## Corrección aplicada

Se añadió `/support` como alias de la pantalla real de soporte para cubrir enlaces o documentación en inglés sin duplicar funcionalidad.

## Protección añadida

`tools/check_v813_routes_links_navigation.py` bloquea:

- rutas críticas ausentes
- enlaces con formato roto tipo `/ruta=valor`
- falta de shell V813
- SHARK flotante visible en `/shark`
- texto técnico evidente en `base.html`
- mojibake visible en `base.html`
