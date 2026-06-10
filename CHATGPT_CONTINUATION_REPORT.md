# ChatGPT Continuation Report — V710 Render Cron Automation Final Setup

## Estado Inicial

NeMeSiS SHARK PRO ya tenía Telegram manual funcionando, canal global probado, cola operativa, picks generados, dedupe activo y endpoints de automatización protegidos con secreto.

La conclusión anterior fue clara: el Web Service de Render no garantiza el scheduler interno. Hace falta Render Cron.

## Trabajo Realizado

Se certificaron los endpoints definitivos:

- `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`
- `/api/automation/daily/run?secret=AUTOMATION_SECRET`

Se verificó:

- sin secreto devuelven 403.
- con secreto devuelven 200.
- registran `last_cron_telegram_call`.
- registran `last_cron_daily_call`.
- no requieren sesión admin.
- están preparados para Render Cron.

## Variables Necesarias

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`
- `DB_PATH=/data/database.db`

## Cron Jobs Necesarios

Cron 1:

`NeMeSiS Telegram Tick`

Cada 15 minutos:

`https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_DE_AUTOMATION_SECRET`

Cron 2:

`NeMeSiS Daily Automation`

Cada hora o diario a las 10:00 Europe/Madrid:

`https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_DE_AUTOMATION_SECRET`

## Estado Telegram

Telegram manual: funciona.

Telegram canal: funciona.

Telegram privado: soportado, pendiente de prueba con usuario real vinculado.

Telegram automático: listo con Render Cron.

Telegram automático sin admin: sí, si Render Cron queda configurado.

## Conclusión

El código ya está listo.

La única pieza externa pendiente es crear los dos Render Cron Jobs con el secreto correcto.

Una vez hecho, NeMeSiS podrá enviar picks automáticamente sin intervención del admin.

