# ChatGPT Continuation Report — V710 Telegram Auto Send Via Render Cron

## Estado Inicial

NeMeSiS SHARK PRO ya tenía Telegram manual funcionando, canal global operativo, token válido, `TELEGRAM_CHAT_ID` válido, cola funcional, picks existentes, scheduler interno y dedupe.

El problema real era que Render Web Service no garantiza ejecución automática de fondo. Por eso el envío automático necesita Render Cron.

## Qué Se Certificó

Endpoints:

- `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`
- `/api/automation/daily/run?secret=AUTOMATION_SECRET`

Ambos:

- existen.
- no dependen de sesión admin.
- bloquean sin secreto.
- responden 200 con secreto válido.
- actualizan diagnóstico.

## Prueba Final

Resultado local controlado:

- Telegram Tick sin secreto: 403.
- Telegram Tick con secreto: 200.
- Estado: `QUEUE_PROCESSED`.
- Mensajes enviados por cola: 2.
- Daily Automation sin secreto: 403.
- Daily Automation con secreto: 200.
- `last_cron_telegram_call`: actualizado.
- `last_cron_daily_call`: actualizado.
- cola pendiente: 0.
- fallidos hoy: 0.
- dedupe activo.
- observability errors: 0.

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

## Cron Jobs a Crear

Cron 1:

`NeMeSiS Telegram Tick`

Cada 15 minutos:

`https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_REAL_DE_AUTOMATION_SECRET`

Cron 2:

`NeMeSiS Daily Automation`

Cada hora o diario a las 10:00 Europe/Madrid:

`https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_REAL_DE_AUTOMATION_SECRET`

## Conclusión

Telegram automático queda listo a nivel de código y configuración documentada.

La única acción externa pendiente es crear los dos Cron Jobs en Render con el secreto real.

Una vez creados, NeMeSiS podrá mandar picks automáticamente sin que el admin toque nada.

