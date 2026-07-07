# V749 Render Cron Setup

## Cron oficial Telegram

Nombre recomendado:

`NeMeSiS Telegram Auto Tick`

Frecuencia recomendada:

Cada 5 o 10 minutos. Si se quiere conservar margen de API y ruido, cada 15 minutos también es válido.

Método:

`GET`

URL:

`https://TU_DOMINIO/api/automation/telegram/tick?secret=***hidden***`

Ejemplo:

`https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=***hidden***`

## Variables Render necesarias

Obligatorias:

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Recomendadas para activar automático:

- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`

Compatibles también:

- `ENABLE_TELEGRAM_AUTOMATION=true`
- `TELEGRAM_AUTO_SEND_ENABLED=true`

Opcionales:

- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_TICK_REVIEW_MINUTES=15`
- `TELEGRAM_DAILY_PICKS_START=13:00`
- `TELEGRAM_DAILY_PICKS_END=20:30`
- `TELEGRAM_DAILY_SUMMARY_START=09:30`
- `TELEGRAM_DAILY_SUMMARY_END=12:30`
- `MIN_SHARK_SCORE_FOR_AUTO_SEND=75`
- `TELEGRAM_MAX_MESSAGES_PER_HOUR=1`
- `TELEGRAM_MAX_MESSAGES_PER_DAY=8`

## Cómo comprobar

Sin secret:

`/api/automation/telegram/tick`

Debe devolver `403`.

Con secret:

`/api/automation/telegram/tick?secret=***hidden***`

Debe devolver `200`.

En admin:

Abrir `/admin/telegram/command-center` y comprobar:

- último Telegram Tick,
- próximo tick esperado,
- último automático,
- último manual,
- fuente `cron`,
- errores recientes.

## Si manual manda pero automático no

Revisar en este orden:

1. Render Cron existe y está activo.
2. La URL incluye el secret real.
3. `AUTOMATION_SECRET` coincide exactamente.
4. `ENABLE_TELEGRAM_AUTO` o `AUTO_SEND_TELEGRAM_PICKS` están activos.
5. `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están configurados.
6. El panel muestra `last_automation_tick_madrid`.
7. Hay picks elegibles con cuota, selección, score y partido válido.
8. El diagnóstico no muestra `DUPLICATE_ALREADY_SENT`, `TOO_EARLY`, `TOO_LATE`, `MISSING_ODDS` o `AUTO_DISABLED`.

