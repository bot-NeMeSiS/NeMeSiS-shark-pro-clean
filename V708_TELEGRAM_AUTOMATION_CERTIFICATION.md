# V708 TELEGRAM AUTOMATION CERTIFICATION

Fecha: 2026-06-10  
Proyecto: NeMeSiS SHARK PRO  
Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`

## 1. Veredicto tecnico

Telegram manual ya funcionaba. El problema pendiente no era el bot, ni el token, ni el chat_id, ni la API de Telegram.

El punto debil real era el disparador de produccion:

- El Web Service de Render no garantiza por si solo una tarea periodica permanente.
- El scheduler interno existia, pero dependia de startup/trafico/configuracion y no era una certificacion fuerte de ejecucion cada X minutos.
- Faltaba un endpoint cron seguro y documentado para que Render Cron ejecute el ciclo sin intervencion del admin.

## 2. Quien dispara ahora el automatico

Produccion debe dispararlo con Render Cron:

- Daily automation: `/api/automation/daily/run?secret=AUTOMATION_SECRET`
- Tick Telegram: `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`

Tambien se mantiene:

- `/api/telegram/scheduler-tick?secret=AUTOMATION_SECRET`

El admin puede seguir usando el panel, pero el flujo de produccion ya no depende de pulsar botones.

## 3. Flujo certificado en codigo

El ciclo automatico ejecuta:

1. `run_daily_autonomous_system()`
2. `run_scheduler_task("recommendations")`
3. `run_scheduler_task("auto_picks")`
4. `refresh_auto_picks_basic()`
5. `ensure_auto_pick_from_recommendation()`
6. `telegram_scheduler_delivery()`
7. `enqueue_auto_pick_alerts()`
8. `process_premium_telegram_queue()`
9. `telegram_send_http()`
10. estado final `sent`

## 4. Canal global

El canal global `TELEGRAM_CHAT_ID` queda como destino obligatorio si esta configurado.

Funciona aunque:

- usuarios vinculados = 0
- usuarios privados = 0
- no haya usuarios PRO/ELITE vinculados

Los privados vinculados se anaden despues segun membresia.

## 5. Variables auditadas

Usadas efectivamente:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO`
- `AUTO_SEND_TELEGRAM_PICKS`
- `AUTO_GENERATE_PICKS`
- `SCHEDULER_ENABLED`
- `DAILY_AUTOMATION_ENABLED`
- `RUN_DAILY_AUTOMATION`
- `RUN_STARTUP_SCHEDULER_NOW`
- `AUTOMATION_SECRET`
- `MIN_SHARK_SCORE_FOR_AUTO_SEND`
- `MAX_AUTO_PICKS_PER_DAY`

Compatibilidad:

- `SCHEDULER_ENABLED` ahora se respeta.
- `DAILY_AUTOMATION_ENABLED` y `RUN_DAILY_AUTOMATION` ahora aparecen en diagnostico.
- `AUTOMATION_SECRET` protege los endpoints cron.

## 6. Trazas

Se registran marcas:

- `[AUTOMATION]`
- `[AUTO_PICKS]`
- `[QUEUE]`
- `[QUEUE_LOAD]`
- `[QUEUE_PROCESS]`
- `[QUEUE_SENT]`
- `[QUEUE_FAIL]`
- `[QUEUE_SKIP_DUPLICATE]`
- `[TELEGRAM]`

## 7. Prueba controlada realizada

Con SQLite temporal y Telegram simulado:

- Endpoint sin secret: `403`
- Endpoint con secret: `200`
- Auto pick generado: `1`
- Picks enviados: `2`
- Telegram task sent: `2`
- Cola pendiente: `0`
- Ultimo auto pick: `sent`
- Chat destino: `-1003951459919`
- Duplicado posterior: omitido por dedupe
- Observability errors: `0`

No se uso `/api/telegram/send`.
No se pulso boton admin.

## 8. Certificacion real de Render

No se puede certificar desde este entorno que Render ya este ejecutando los cron jobs, porque no hay acceso autenticado a logs/servicio Render en esta sesion.

Lo que si queda listo:

- endpoint seguro
- secret
- variables
- diagnostico
- logs
- dedupe
- envio al canal global
- cola automatica

La certificacion final en produccion se obtiene mirando:

- `/admin/telegram/diagnostics`
- `telegram_logs`
- `telegram_queue`
- logs de Render Cron

