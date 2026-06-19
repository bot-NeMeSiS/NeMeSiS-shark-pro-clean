# V815 Routes Links Navigation QA

## Resultado

`tools/check_v815_routes_links_navigation.py` valida rutas cliente/admin, enlaces core, cache-busting y capa V815.

## Cliente validado

- `/`
- `/app`
- `/calendar`
- `/partidos`
- `/live`
- `/picks`
- `/match/<match_id>`
- `/shark`
- `/shark-core`
- `/profile`
- `/telegram`
- `/favorites`
- `/track-record`
- `/support`

## Admin validado

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

## SHARK

- Un solo widget flotante en `base.html`.
- `/shark` oculta el flotante por CSS.
- El boton no tapa bottom nav: se fija por encima de la navegacion movil.
