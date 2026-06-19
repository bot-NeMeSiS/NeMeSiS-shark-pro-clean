# V817 Runtime Visibility QA

## Version

`V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL`

## Comprobaciones esperadas

- `VERSION.txt` y `APP_VERSION` coinciden.
- `/api/runtime-version` devuelve `has_v817_shell` y `has_v817_css`.
- `templates/base.html` contiene `NEMESIS V817 REFERENCE PIXEL POLISH ACTIVE`.
- `body` contiene `data-v817-shell="true"`.
- `app.css` carga con `?v=V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL`.
- El CSS contiene la capa final V817.

## Herramienta

`tools/check_v817_runtime_visibility.py`

## Resultado ejecutado

- `VERSION.txt`: OK.
- `APP_VERSION`: OK.
- `has_v817_shell`: OK.
- `has_v817_css`: OK.
- `static_css_cache_busting`: OK.
- Smoke `/api/runtime-version`: devuelve V817.
- ZIP final V817: raiz correcta, sin proyecto anidado.
