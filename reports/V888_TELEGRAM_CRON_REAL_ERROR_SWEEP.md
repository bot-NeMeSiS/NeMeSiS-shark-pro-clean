# V888 Telegram Cron Real Error Sweep

## Revisión

Se revisaron:

- `/api/automation/telegram/tick`
- `process_premium_telegram_queue`
- `telegram_scheduler_tick`
- import de estados de cola en `app.py`
- `engines/telegram_delivery_engine.py`
- dedupe y calidad Telegram

## Estado del bug V887

`QUEUE_SKIPPED` está definido como `skipped` en el motor de entrega y ahora está importado en `app.py`.

## Validación local esperada

- Cron sin secret: `403`.
- Cron con secret local y `runner=render_cron`: `200`.
- Sin `NameError`.
- Sin envío real porque el entorno local de prueba usa token/chat vacíos.

## Producción

Render sigue en V883. No se puede certificar el fix V887/V888 en producción hasta deploy.

## Reglas preservadas

- No filler.
- Dedupe.
- Límite diario.
- `AUTOMATION_SECRET`.
- Sin Telegram real sin autorización.

