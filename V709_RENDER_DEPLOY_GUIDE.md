# V709 Render Deploy Guide

## Variables Obligatorias en Render

Configurar en el Web Service:

- `AUTOMATION_SECRET`: secreto largo y privado para Cron.
- `TELEGRAM_BOT_TOKEN`: token real del bot.
- `TELEGRAM_CHAT_ID`: canal global, por ejemplo `-1003951459919`.
- `ENABLE_TELEGRAM_AUTO=true`.
- `AUTO_SEND_TELEGRAM_PICKS=true`.
- `AUTO_GENERATE_PICKS=true`.
- `SCHEDULER_ENABLED=true`.
- `DB_PATH=/data/database.db`.

## Cron 1

Nombre:

`Telegram Scheduler`

Frecuencia:

Cada 15 minutos.

Método:

`GET`

URL exacta:

`https://nemesis-shark-pro.onrender.com/api/automation/telegram/tick?secret=TU_AUTOMATION_SECRET`

Qué hace:

- revisa cola Telegram.
- encola auto picks elegibles.
- envía al canal global.
- envía privados vinculados si existen.
- evita duplicados.
- registra última ejecución.

## Cron 2

Nombre:

`Daily Automation`

Frecuencia recomendada:

Cada hora durante el día deportivo o una vez al día si se quiere menor consumo.

Método:

`GET`

URL exacta:

`https://nemesis-shark-pro.onrender.com/api/automation/daily/run?secret=TU_AUTOMATION_SECRET`

Qué hace:

- sincroniza calendario.
- refresca live.
- genera recomendaciones.
- genera auto picks.
- ejecuta entrega Telegram.
- crea backup.
- registra última ejecución.

## Validación Posterior en Producción

Después de crear los Cron Jobs:

1. Abrir `/admin/telegram/diagnostics`.
2. Confirmar `last_cron_telegram_call` actualizado.
3. Confirmar `last_scheduler_tick` actualizado.
4. Confirmar `last_cron_daily_call` actualizado.
5. Confirmar `last_daily_automation` actualizado.
6. Revisar `last_auto_pick`.
7. Revisar `last_sent`.
8. Confirmar `pending=0` o cola justificada.
9. Confirmar que no hay errores recientes.

## Nota Sobre Dominio

Si Render usa dominio personalizado, sustituir:

`https://nemesis-shark-pro.onrender.com`

por el dominio real de producción.

La ruta y el parámetro `secret` deben mantenerse igual.

