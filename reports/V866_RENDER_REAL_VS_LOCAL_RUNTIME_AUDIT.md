# V866 Render real vs runtime local

## Base
- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.
- Base local confirmada antes de V866: `V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL`.
- No se usó ZIP viejo ni carpeta anidada.

## Render real
- URL consultada: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
- Resultado: HTTP 200.
- Versión publicada en Render durante la auditoría: `V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL`.
- `db_path`: `/data/database.db`.
- `automation_secret_configured`: true.
- `telegram_configured`: true.
- `api_football_configured`: true.
- `api_sports_configured`: true.
- `api_sports_provider_available`: true.
- `the_odds_configured`: true.
- `openai_configured`: false.
- `provider_active`: `api-sports/api-football`.
- `last_sync`: `2026-06-30T16:14:00Z`.
- `usage_guard`: cache-first y sin llamadas por render según runtime.

## Diferencia principal
Render expuso `last_error` con un mensaje de cabecera inválida:
`Invalid header value b'386760cfa00b37f98d680113043f9768\n'`.

V866 no elimina el diagnóstico, pero limpia saltos reales y literales `\n`/`\r` antes de exponerlo por runtime.

## Local
- `/api/runtime-version` local respondió 200 con base V865 antes de actualizar.
- En local, sin variables reales cargadas, los flags de Telegram/API/OpenAI/Odds salían false. Esto es correcto para entorno local y no implica fallo de Render.

## Honestidad
- No se hizo deploy.
- No se tocaron secretos.
- No se afirmó que Render tenga V866 hasta que se despliegue.
