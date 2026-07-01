# V873 runtime real Render QA

## Endpoint

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

## Datos observados

- `app_version`: `V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL`.
- `version_txt`: `V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL`.
- `db_path`: `/data/database.db`.
- `static_app_css_hash`: `8c19317ceb4f57a1`.
- `static_app_css_size`: `877841`.
- `last_error`: `Invalid header value ...`.
- `openai_configured`: `false`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `telegram_configured`: `true`.
- `the_odds_configured`: `true`.
- `api_sports_configured`: `true`.
- `automation_secret_configured`: `true`.
- `provider_active`: `api-sports/api-football`.
- `usage_guard.no_page_render_calls`: `true`.

## OK

- Producción está alineada en V871.
- API-SPORTS/API-Football configurado.
- The Odds API configurado.
- Telegram configurado.
- Master automation protegido por secret configurado.
- Guard anti-gasto activo.

## Warning

- `last_error` mantiene un error histórico de cabecera inválida.
- OpenAI no está configurado; SHARK debe comunicar modo seguro/fallback.
- Cache de logos a cero; la app debe usar fallback premium y no inventar escudos.

## Blocker

- V873 no está desplegada. No se puede afirmar que producción muestre V873 hasta deploy manual.

## Next action

Desplegar V873, confirmar runtime sin `Invalid header value` crudo, validar fallback de logos y capturar producción real.
