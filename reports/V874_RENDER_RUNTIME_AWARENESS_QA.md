# V874 Render Runtime Awareness QA

## Producción real

Runtime consultado: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.

- Producción sigue en `V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL`.
- `last_error`: `Invalid header value b'386760cfa00b37f98d680113043f9768'`.
- `openai_configured`: `false`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `telegram_configured`: `true`.
- `the_odds_configured`: `true`.
- `api_sports_configured`: `true`.
- `automation_secret_configured`: `true`.
- `db_path`: `/data/database.db`.

## Local

- V874 se prepara localmente.
- No se declara Render V874 hasta deploy manual.
- No se tocaron secretos ni configuración real.

## Clasificación

- OK: Render responde runtime y V818/V844/V847/V850/V871 siguen presentes.
- Warning: producción no tiene V873/V874 desplegado todavía.
- Warning: OpenAI no configurado; SHARK debe mostrar modo seguro.
- Warning: caché de logos en cero; fallback premium obligatorio.
- Warning: `last_error` histórico de header debe validarse tras deploy V874.

