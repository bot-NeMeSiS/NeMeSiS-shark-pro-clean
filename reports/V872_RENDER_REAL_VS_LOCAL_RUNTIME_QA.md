# V872 Render real vs runtime local

## Render real consultado

Endpoint: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado:

- `app_version`: `V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL`.
- `version_txt`: `V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL`.
- `app_py_path`: `/opt/render/project/src/app.py`.
- `db_path`: `/data/database.db`.
- `static_app_css_hash`: `8c19317ceb4f57a1`.
- `static_app_css_size`: `877841`.
- `automation_secret_configured`: `true`.
- `telegram_configured`: `true`.
- `api_football_configured`: `true`.
- `api_sports_configured`: `true`.
- `api_sports_provider_available`: `true`.
- `the_odds_configured`: `true`.
- `openai_configured`: `false`.
- `provider_active`: `api-sports/api-football`.
- `last_sync`: `2026-06-30T22:33:03Z`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `usage_guard.no_page_render_calls`: `true`.

## Diferencias y riesgos

- Render está en V871, por tanto puede certificarse que producción muestra V871, no V872.
- Render tiene `last_error`: `Invalid header value ...`. En V872 se refuerza el saneado local para no exponer el valor crudo en runtime.
- Las cachés de logos de equipo/liga aparecen en `0`. No se inventan escudos: si no hay caché, debe usarse fallback visual premium.
- OpenAI no está configurado en Render. SHARK debe seguir con fallback seguro.

## Estado

No hay blocker por mismatch V871, porque producción sí está en V871. El blocker pendiente es operativo: V872 no estará en producción hasta deploy manual.
