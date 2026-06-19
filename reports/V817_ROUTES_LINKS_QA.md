# V817 Routes Links QA

## Herramienta

`tools/check_v817_routes_links_navigation.py`

## Cobertura

Cliente:

- `/`
- `/cliente-login`
- `/app`
- `/calendar`
- `/partidos`
- `/live`
- `/directo`
- `/picks`
- `/match/<match_id>`
- `/shark`
- `/shark-core`
- `/profile`
- `/telegram`
- `/favorites`
- `/track-record`
- `/support`

Admin:

- `/admin/dashboard`
- `/admin/map`
- `/admin/control-center`
- `/admin/telegram/command-center`
- `/admin/telegram/pro-preview`
- `/admin/users`
- `/admin/memberships`
- `/admin/matches-sync`
- `/admin/data-center`
- `/admin/automation-center`

## Criterios

El check falla si falta V817 en CSS/base, si hay hrefs mal formados, si falta SHARK unico o si faltan rutas criticas.

## Resultado ejecutado

- `tools/check_v817_routes_links_navigation.py`: OK.
- Smoke Flask sin 500 en rutas cliente y admin criticas.
- Rutas protegidas redirigen correctamente a login cuando no hay sesion.
- Con sesion simulada ELITE/admin, las pantallas renderizan V817 y sin incidencia controlada.
