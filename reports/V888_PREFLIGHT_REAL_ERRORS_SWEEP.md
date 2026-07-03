# V888 Preflight Real Errors Sweep

## Base local

- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- Versión local antes de V888: `V887_TELEGRAM_QUEUE_SKIPPED_RUNTIME_HOTFIX_FINAL`
- Nueva versión: `V888_REAL_ERRORS_SWEEP_TELEGRAM_MATCHES_PICKS_NAV_SENTINEL_FINAL`

## Render real consultado

- URL: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
- Versión Render observada: `V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL`
- `app_py_path`: `/opt/render/project/src/app.py`
- `current_working_directory`: `/opt/render/project/src`
- `db_path`: `/data/database.db`
- `static_app_css_hash`: `a7107f484eaa3dcd`
- `last_error`: histórico saneado de `Invalid header value`
- `openai_configured`: `false`
- `team_logo_cache_count`: `0`
- `league_logo_cache_count`: `0`
- `telegram_configured`: `true`
- `api_sports_configured`: `true`
- `the_odds_configured`: `true`

## Estado de alineación

Render no está alineado con local. Producción sirve V883, por lo que V887/V888 no pueden declararse corregidas en producción hasta deploy manual.

## Git local

- `.git` existe.
- Remote en `.git/config`: `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`
- Rama configurada: `main`
- HEAD local: `6a16768089885aae717ba2787aff6c2a31e3c584`
- `git` no está disponible en PATH ni en la ruta antigua de GitHub Desktop, por lo que no se pudo calcular `ahead/behind` real en esta pasada.

## Bloqueador real

Primero hay que desplegar el contenido local actual. Mientras Render siga en V883, los fixes V887/V888 no se verán en producción.

