# V867 real Render runtime QA

## Estado real comprobado
Se consultó producción real en:
`https://bot-apuestas-crgf.onrender.com/api/runtime-version`.

Resultado:
- HTTP 200.
- `app_version`: `V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL`.
- `version_txt`: `V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL`.
- `has_v866_real_render_visual_telegram_picks_payments`: true.
- `db_path`: `/data/database.db`.
- `telegram_configured`: true.
- `the_odds_configured`: true.
- `api_sports_configured`: true.
- `api_football_configured`: true.
- `automation_secret_configured`: true.

## V867
V867 no se desplegó desde Codex porque no había autorización para push/deploy automático.

Estado V867 en Render:
- Pendiente de deploy manual.

## Criterio posterior al deploy manual
Tras desplegar V867, `/api/runtime-version` debe devolver:
- `app_version`: `V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL`.
- `version_txt`: `V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL`.
- `has_v867_render_deployment_alignment`: true.
- `has_v866_real_render_visual_telegram_picks_payments`: true.
