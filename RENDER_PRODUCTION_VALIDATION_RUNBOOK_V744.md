# Render Production Validation Runbook V744

## Variables mínimas

- `SECRET_KEY`
- `DB_PATH=/data/database.db`
- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `DAILY_AUTOMATION_ENABLED=true`

## Cron Jobs recomendados

Telegram cada 15 minutos:

- `GET https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_REAL`

Daily automation cada hora o 10:00 Europe/Madrid:

- `GET https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_REAL`

Backup diario si se activa:

- `GET https://bot-apuestas-crgf.onrender.com/api/automation/data-backup/run?secret=VALOR_REAL`

## Validación

1. Abrir `/api/runtime-version`.
2. Verificar `automation_secret_configured=true`.
3. Llamar cron sin secret y confirmar 403.
4. Llamar cron con secret y confirmar 200.
5. Revisar `/admin/telegram/diagnostics`.
6. Revisar `/admin/data-vault`.
