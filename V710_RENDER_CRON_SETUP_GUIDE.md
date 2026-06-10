# V710 Render Cron Setup Guide

## Paso 1 — Variables del Web Service

En Render, abrir el Web Service de NeMeSiS SHARK PRO y configurar:

- `AUTOMATION_SECRET`: valor largo, privado y aleatorio.
- `TELEGRAM_BOT_TOKEN`: token real del bot.
- `TELEGRAM_CHAT_ID`: canal global real.
- `TELEGRAM_BOT_USERNAME`: usuario del bot sin `@` o con `@`.
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`
- `DB_PATH=/data/database.db`

## Cron Job 1

Nombre:

`NeMeSiS Telegram Tick`

Frecuencia:

Cada 15 minutos.

Método:

`GET`

URL:

`https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_DE_AUTOMATION_SECRET`

Objetivo:

- procesar cola Telegram.
- preparar auto picks elegibles.
- enviar al canal global.
- enviar privados vinculados si existen.
- evitar duplicados.
- registrar última ejecución.

## Cron Job 2

Nombre:

`NeMeSiS Daily Automation`

Frecuencia recomendada:

Cada hora durante el día deportivo o diario a las 10:00 Europe/Madrid.

Método:

`GET`

URL:

`https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_DE_AUTOMATION_SECRET`

Objetivo:

- actualizar partidos.
- actualizar live.
- generar recomendaciones.
- generar picks.
- procesar Telegram.
- crear backup.
- registrar automatización diaria.

## Validación Tras Configurar Cron

Abrir:

`https://bot-apuestas-crgf.onrender.com/admin/telegram/diagnostics`

Comprobar:

- `last_cron_telegram_call` tiene hora reciente.
- `last_cron_daily_call` tiene hora reciente.
- `last_scheduler_tick` se actualiza.
- `last_daily_automation` se actualiza.
- `automatic_status` aparece como `preparado` o `funcionando`.
- `pending` baja tras cada tick.
- `failed_today` queda en 0 o con error claro.

## Resultado Esperado

Una vez creados los Cron Jobs:

Render ejecuta la automatización sin visitas web y sin acciones del admin.

