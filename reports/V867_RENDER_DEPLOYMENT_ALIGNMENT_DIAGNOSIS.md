# V867 Render deployment alignment diagnosis

## Base local
- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.
- Base local antes de V867: `V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL`.
- ZIP local base V866: `release_output/NeMeSiS_SHARK_PRO_V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL_RENDER_READY.zip`.
- No se usó ZIP viejo V827.
- No se usó carpeta anidada.
- No se hizo push.
- No se hizo deploy automático.

## Runtime Render real consultado
- URL: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
- HTTP status: 200.
- Producción real observada durante V867: `V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL`.
- `version_txt`: `V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL`.
- `app_py_path`: `/opt/render/project/src/app.py`.
- `current_working_directory`: `/opt/render/project/src`.
- `db_path`: `/data/database.db`.
- `static_app_css_hash`: `3be978412472997c`.
- `static_app_css_size`: `844866`.
- `static_app_css_mtime`: `2026-06-30T23:37:30+02:00`.
- `has_v866_real_render_visual_telegram_picks_payments`: true.
- `automation_secret_configured`: true.
- `telegram_configured`: true.
- `api_football_configured`: true.
- `api_sports_configured`: true.
- `api_sports_provider_available`: true.
- `the_odds_configured`: true.
- `openai_configured`: false.
- `provider_active`: `api-sports/api-football`.
- `last_sync`: `2026-06-30T16:14:00Z`.
- `usage_guard.no_page_render_calls`: true.

## Header error
Render seguía mostrando el diagnóstico:
`Invalid header value b'386760cfa00b37f98d680113043f9768'`.

Importante: ya no contiene salto de línea real ni literal `\n` en runtime. V866 saneó correctamente el valor visible.

## Diagnóstico final
La situación indicada en el prompt decía que producción seguía en V862. En la comprobación real V867, producción ya estaba alineada con V866.

## Acción aplicada
Se crea V867 como versión de certificación/alineación, sin features nuevas, para dejar paquete limpio y trazabilidad de que Render ya sirve V866 y que V867 queda listo para deploy manual si se desea.

## Acción pendiente
Deploy manual de V867 si se quiere que producción devuelva `V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL`.
