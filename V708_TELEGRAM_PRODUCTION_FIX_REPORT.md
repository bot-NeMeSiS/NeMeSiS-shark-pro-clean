# V708 TELEGRAM PRODUCTION FIX REPORT

## Causa raiz

El envio manual funcionaba porque el admin disparaba explicitamente:

`/api/telegram/send -> enqueue -> process_premium_telegram_queue -> telegram_send_http`

El automatico fallaba como producto porque no habia un disparador de produccion garantizado. El scheduler interno podia existir, pero no aseguraba ejecucion periodica real en Render sin Cron.

Ademas, el motor de auto picks solo contaba candidatos en algunas versiones, por lo que podia no materializar picks reales para Telegram.

Durante la validacion V708 aparecio otro fallo real:

- `process_premium_telegram_queue()` escribia logs mientras aun mantenia abierta la transaccion de actualizacion de cola.
- Eso podia provocar `sqlite3.OperationalError: database is locked`.
- Se corrigio cerrando la transaccion antes de registrar logs.

## Correcciones aplicadas

Archivo principal:

- `app.py`

Cambios:

- Endpoint cron seguro `/api/automation/daily/run`.
- Endpoint cron seguro `/api/automation/telegram/tick`.
- `/api/telegram/scheduler-tick` protegido por admin o `AUTOMATION_SECRET`.
- Soporte efectivo para `SCHEDULER_ENABLED`.
- Diagnostico de `DAILY_AUTOMATION_ENABLED`, `RUN_DAILY_AUTOMATION`, `AUTO_GENERATE_PICKS`.
- Auto picks persistidos desde recomendaciones con cuota valida.
- Canal global obligatorio mediante `telegram_auto_destinations()`.
- Encolado automatico `auto_pick`.
- Dedupe por `pick_id + chat_id`.
- Logs `[AUTOMATION]`, `[AUTO_PICKS]`, `[QUEUE_*]`.
- Fix de `database is locked` en logs de cola.
- `.env.example` y `.env.render.clean` actualizados.

## Que funciona

- Manual sigue funcionando.
- Canal global es destino obligatorio del automatico.
- Privados se anaden por membresia si existen.
- Endpoint cron rechaza sin secret.
- Endpoint cron ejecuta el ciclo sin boton admin.
- Cola queda `pending -> sent`.
- Duplicados se evitan.

## Que no puede demostrarse desde aqui

No puedo confirmar que Render Cron ya este creado ni que haya ejecutado en produccion, porque esta sesion no tiene acceso autenticado a Render.

Para certificar produccion hace falta crear los Cron Jobs indicados y revisar logs reales de Render.

## Resultado de prueba controlada

Con SQLite temporal y Telegram simulado:

- `unauth_status=403`
- `daily_status=200`
- `picks_generated=1`
- `picks_sent=2`
- `telegram_sent=2`
- `pending=0`
- `last_auto_pick_status=sent`
- `last_auto_pick_chat=-1003951459919`
- `duplicates_avoided=2`
- `observability_errors=0`

No se uso `/api/telegram/send`.

