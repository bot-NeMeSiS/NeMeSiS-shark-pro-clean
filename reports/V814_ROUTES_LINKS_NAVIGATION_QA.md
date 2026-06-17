# V814 Routes Links Navigation QA

## Cliente validado por check

- `/`
- `/app`
- `/calendar`
- `/partidos`
- `/live`
- `/directo`
- `/picks`
- `/match/<id>`
- `/team/<id>`
- `/shark`
- `/shark-core`
- `/telegram`
- `/profile`
- `/perfil`
- `/mi-cuenta`
- `/favorites`
- `/track-record`
- `/support`
- `/soporte`
- `/logout`

## Admin validado por check

- `/admin/dashboard`
- `/admin/map`
- `/admin/control-center`
- `/admin/users`
- `/admin/memberships`
- `/admin/matches-sync`
- `/admin/data-center`
- `/admin/data-memory`
- `/admin/data-vault`
- `/admin/automation-center`
- `/admin/telegram/command-center`
- `/admin/telegram/pro-preview`
- `/admin/live-depth`
- `/admin/final-certification`
- `/admin/payments`
- `/admin/track-record`
- `/admin/highlights-center`
- `/admin/visual-experience`
- `/admin/go-live`
- `/admin/client-success`
- `/admin/public-launch`
- `/admin/route-health`
- `/admin/client-experience`
- `/admin/sale-ready`
- `/admin/final-release`

## Protección

`tools/check_v814_routes_links_navigation.py` falla si detecta:

- ruta crítica ausente;
- query string mal formada;
- SHARK duplicado;
- cliente sin logout;
- shell V814 ausente;
- texto técnico en `base.html`;
- mojibake visible en `base.html`.
