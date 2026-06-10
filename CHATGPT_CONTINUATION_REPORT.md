# CHATGPT CONTINUATION REPORT

## 1. Causa raiz exacta

Telegram manual funcionaba. El problema real estaba en que el automatico no tenia un disparador de produccion garantizado en Render. Un Web Service no asegura tareas periodicas por si solo. Hacia falta Render Cron o un equivalente externo.

Tambien se reforzo la generacion real de auto picks y se corrigio un bloqueo SQLite detectado en cola.

## 2. Que fallaba en automatico

Fallaba la garantia de ejecucion sin admin. El sistema tenia funciones internas, pero no habia una ruta cron segura y documentada como contrato de produccion.

## 3. Que si funcionaba manualmente

Funcionaba:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `/api/telegram/send`
- cola manual
- canal Telegram

## 4. Que se corrigio

- Se crearon endpoints cron seguros.
- Se anadio `AUTOMATION_SECRET`.
- Se conecto auto-pick real al ciclo.
- Se aseguro canal global obligatorio.
- Se reforzo dedupe.
- Se mejoro diagnostico admin.
- Se corrigio `database is locked` al loguear tras envio.

## 5. Endpoints automaticos

- `/api/automation/daily/run?secret=...`
- `/api/automation/telegram/tick?secret=...`
- `/api/telegram/scheduler-tick?secret=...`

## 6. Variables Render obligatorias

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`
- `RUN_DAILY_AUTOMATION=true`
- `AUTOMATION_SECRET=...`

## 7. Necesita Render Cron

Si. Para certificar que el admin no toca nada, Render debe ejecutar Cron Jobs contra los endpoints seguros.

## 8. Como probar en produccion

1. Configurar variables Render.
2. Crear Cron diario para `/api/automation/daily/run?secret=...`.
3. Crear Cron cada 15 minutos para `/api/automation/telegram/tick?secret=...`.
4. Mirar `/admin/telegram/diagnostics`.
5. Confirmar `last_auto_pick.status=sent`.
6. Confirmar `pending=0`.
7. Confirmar mensaje recibido en canal.

## 9. Logs que mirar

- `[AUTOMATION]`
- `[AUTO_PICKS]`
- `[QUEUE_LOAD]`
- `[QUEUE_PROCESS]`
- `[QUEUE_SENT]`
- `[QUEUE_FAIL]`
- `[TELEGRAM]`

## 10. Si no llega mensaje

Revisar:

- falta `AUTOMATION_SECRET`
- Render Cron no creado
- `ENABLE_TELEGRAM_AUTO=false`
- `AUTO_SEND_TELEGRAM_PICKS=false`
- no hay cuotas validas
- score por debajo de `MIN_SHARK_SCORE_FOR_AUTO_SEND`
- cola `failed`
- error real de Telegram en `last_error`

