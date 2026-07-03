# V887 Telegram QUEUE_SKIPPED Error Audit

## Base revisada

- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- Base local antes del hotfix: `V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL`
- Error real reportado en Render Cron: `[CRON_ENDPOINT_ERROR] telegram_tick: name 'QUEUE_SKIPPED' is not defined`
- Endpoint afectado: `/api/automation/telegram/tick?secret=...&runner=render_cron`

## Búsqueda realizada

Se revisaron:

- `app.py`
- `engines/telegram_delivery_engine.py`
- motores `engines/telegram*.py`
- checks y herramientas relacionadas con Telegram
- referencias `QUEUE_`, `DELIVERY_`, `TELEGRAM_`, `SKIPPED`, `SENT`, `FAILED`

## Causa raíz

`engines/telegram_delivery_engine.py` ya definía los estados principales de cola:

- `QUEUE_PENDING = "pending"`
- `QUEUE_SENDING = "sending"`
- `QUEUE_SENT = "sent"`
- `QUEUE_FAILED = "failed"`
- `QUEUE_SKIPPED = "skipped"`

El problema estaba en `app.py`: el bloque de import desde `engines.telegram_delivery_engine` importaba `QUEUE_PENDING`, `QUEUE_SENT`, `QUEUE_SENDING` y `QUEUE_FAILED`, pero no importaba `QUEUE_SKIPPED`.

La rama afectada está en `process_premium_telegram_queue()`. Cuando un mensaje automático supera el límite diario PRO, actualiza la fila de `telegram_queue` con estado saltado:

`QUEUE_SKIPPED`

Al no estar importado en `app.py`, Python lanzaba `NameError` durante el tick de Cron.

## Decisión V887

No se creó un estado nuevo. Se reutilizó el estado existente y coherente:

`QUEUE_SKIPPED = "skipped"`

Motivo:

- mantiene compatibilidad con la cola actual;
- respeta el patrón de estados en minúsculas;
- no cambia no filler;
- no cambia dedupe;
- no inventa envíos;
- no toca Telegram real.

## Riesgo evitado

V887 evita que una rama válida de omisión por límite diario rompa todo el endpoint Cron. El comportamiento esperado pasa a ser:

- mensaje omitido de forma controlada;
- estado `skipped` persistido;
- error seguro si aplica;
- endpoint sin `NameError`.

