# V884 Real Render Deployment State QA

## Endpoint consultado
`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

## Render real
- Version real Render: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`
- Version local: `V884_REAL_RENDER_VISUAL_WORKER_MATCHES_QA_AND_FIX_FINAL`
- V883 desplegada: no.
- V884 desplegada: no.
- `app_py_path`: `/opt/render/project/src/app.py`
- `current_working_directory`: `/opt/render/project/src`
- `db_path`: `/data/database.db`
- `static_app_css_hash`: `163b2a20d9d1af94`
- `last_error`: `Invalid header value b'386760cfa00b37f98d680113043f9768\n'`
- `openai_configured`: false
- `telegram_configured`: true
- `api_sports_configured`: true
- `api_football_configured`: true
- `the_odds_configured`: true
- `team_logo_cache_count`: 0
- `league_logo_cache_count`: 0
- `usage_guard.no_page_render_calls`: true

## Blocker
Produccion no sirve V883/V884. El Visual Worker no puede trabajar sobre produccion hasta que el deploy manual alinee Render con el ZIP local.

## Accion segura
Seguir probando local y preparar deploy manual con clear build cache.
