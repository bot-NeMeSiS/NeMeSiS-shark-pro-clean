# V710 Render Cron Setup Guide

## Objetivo

Crear dos Render Cron Jobs para que NeMeSiS SHARK PRO envíe Telegram automáticamente sin intervención del administrador.

## Variables Obligatorias

En el Web Service de Render configurar:

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

## Cron 1

Nombre:

`NeMeSiS Telegram Tick`

Frecuencia:

Cada 15 minutos.

Método:

`GET`

URL:

`https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_REAL_DE_AUTOMATION_SECRET`

Objetivo:

- procesar cola Telegram.
- preparar auto picks.
- aplicar dedupe.
- enviar al canal global.
- enviar a privados vinculados si existen.
- marcar mensajes como `sent`.
- registrar `last_cron_telegram_call`.

## Cron 2

Nombre:

`NeMeSiS Daily Automation`

Frecuencia:

Cada hora o diario a las 10:00 Europe/Madrid.

Método:

`GET`

URL:

`https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_REAL_DE_AUTOMATION_SECRET`

Objetivo:

- actualizar partidos.
- actualizar live.
- generar recomendaciones.
- generar picks.
- procesar Telegram.
- crear backup.
- registrar `last_cron_daily_call`.

## Validación

Después de crear los Cron Jobs, abrir:

`https://bot-apuestas-crgf.onrender.com/admin/telegram/diagnostics`

Comprobar:

- `last_cron_telegram_call` actualizado.
- `last_cron_daily_call` actualizado.
- `automatic_status` en `preparado` o `funcionando`.
- `chat_id_present=true`.
- `env_flags.AUTOMATION_SECRET=true`.
- `pending=0` o cola justificada.
- `failed_today=0` o error explícito.
- `last_sent` actualizado si había mensajes.

## Resultado Esperado

Render llama automáticamente.

El admin no pulsa nada.

Telegram recibe picks cuando hay oportunidades válidas.

