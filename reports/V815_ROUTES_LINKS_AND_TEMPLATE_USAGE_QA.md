# V815 Routes Links and Template Usage QA

## Resultado

`tools/check_v815_routes_links_navigation.py` pasa correctamente.

## Rutas cliente validadas

- `/`
- `/app`
- `/calendar`
- `/partidos`
- `/live`
- `/picks`
- `/match/<match_id>`
- `/shark`
- `/profile`
- `/telegram`

## Rutas admin revisadas

- `/admin/dashboard`
- `/admin/map`
- `/admin/control-center`
- `/admin/telegram/command-center`
- `/admin/telegram/pro-preview`
- `/admin/users`
- `/admin/matches-sync`
- `/admin/data-center`

## Enlaces core verificados

Cliente:

- `/app`
- `/calendar`
- `/live`
- `/picks`
- `/shark`
- `/logout`

Admin:

- `/admin/control-center`
- `/admin/users`
- `/admin/data-center`
- `/admin/telegram/command-center`

## Nota

Las expresiones Jinja dinamicas tipo `href="{{ item.href }}"` se consideran validas. El check solo marca `None` o `undefined` reales fuera de expresiones Jinja.
