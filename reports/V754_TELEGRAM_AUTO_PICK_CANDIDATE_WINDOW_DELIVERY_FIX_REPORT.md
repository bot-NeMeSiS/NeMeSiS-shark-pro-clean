# V754 Telegram Auto Pick Candidate Window Delivery Fix

## Resumen

V754 corrige el bloqueo real detectado tras V753: Render Cron ejecutaba correctamente y Telegram estaba configurado, pero el tick terminaba con `sent_count=0` porque la lógica interna mezclaba estados de resumen diario, ventanas horarias, candidatos de picks y dedupe.

La corrección mantiene intacto Render Cron, `AUTOMATION_SECRET`, el runner `tools/render_cron_telegram_tick.py`, Telegram manual y el formato premium V751/V752.

## Causa raíz

1. `OUTSIDE_PRO_WINDOW` podía representar el resumen diario o el horario silencioso general, pero acababa dominando la lectura del tick completo.
2. `enqueue_auto_pick_alerts()` seguía usando una lógica antigua de filtros directos y no la auditoría central de candidatos.
3. El procesador de cola solo devolvía contadores globales, sin indicar si lo enviado era `auto_pick`, resumen o alerta live.
4. Algunos dedupes manuales no declaraban explícitamente `source=manual_admin`, lo que hacía menos clara la separación frente a `automatic_cron`.
5. La decisión de partido antiguo dependía de fechas/hora sin un punto único de conversión Madrid para picks automáticos.

## Correcciones aplicadas

- Se añadió una ventana específica para auto picks:
  - `TELEGRAM_PICK_SEND_WINDOW_HOURS_BEFORE=24`
  - `TELEGRAM_PICK_SEND_MIN_MINUTES_BEFORE=15`
  - Naive datetime se interpreta como Madrid.
  - UTC con zona se convierte a Europe/Madrid.
- Se añadió ventana separada para resúmenes:
  - `TELEGRAM_SUMMARY_MORNING_WINDOW=09:00-11:30`
  - `TELEGRAM_SUMMARY_EVENING_WINDOW=17:00-19:30`
- `auto_pick` deja de estar bloqueado por horario silencioso salvo que se active explícitamente:
  - `TELEGRAM_AUTO_PICK_RESPECT_QUIET_HOURS=true`
- `enqueue_auto_pick_alerts()` ahora usa `find_auto_telegram_pick_candidates()`.
- El canal global `TELEGRAM_CHAT_ID` se acepta como destino automático aunque no existan privados vinculados.
- El dedupe automático se calcula por:
  - source
  - message_type
  - pick_id
  - match_id
  - market
  - destination
  - Madrid date
- El procesador de cola devuelve `sent_items`, `failed_items` y `skipped_items`.
- `/api/automation/telegram/tick` devuelve `modules.summary`, `modules.auto_picks` y `modules.live_alerts`.
- El estado principal queda en `SENT` si se envía al menos un auto pick aunque el resumen esté fuera de ventana.
- Se creó `/api/admin/telegram/auto-candidates`.
- El Command Center muestra bloque V754 de candidatos, ventana, siguiente candidato y dedupe.
- Los botones manuales usan dedupe con `source=manual_admin`.

## Estados esperados

Caso con resumen fuera de ventana y pick válido:

```json
{
  "status": "SENT",
  "sent_count": 1,
  "modules": {
    "summary": {"status": "OUTSIDE_PRO_WINDOW", "sent": 0},
    "auto_picks": {"status": "SENT", "sent": 1},
    "live_alerts": {"status": "NO_LIVE_ALERTS", "sent": 0}
  }
}
```

Caso sin candidatos:

```json
{
  "status": "NO_ELIGIBLE_PICKS",
  "sent_count": 0,
  "modules": {
    "auto_picks": {"status": "NO_ELIGIBLE_PICKS"}
  }
}
```

Caso de segundo tick real sobre el mismo pick/destino:

```json
{
  "status": "DUPLICATE_ALREADY_SENT",
  "sent_count": 0
}
```

## Validación

Se añadió `tools/check_v754_telegram_auto_pick_candidate_window_delivery.py`.

El check usa DB temporal y sender Telegram simulado. No manda mensajes reales.

Valida:

- secret ausente devuelve 403.
- secret + runner devuelve 200.
- `cron_runner_detected=true`.
- respuesta con módulos separados.
- pick futuro Madrid genera `SENT`.
- segundo tick genera `DUPLICATE_ALREADY_SENT`.
- pick viejo genera `OLD_MATCH`.
- canal global recibe aunque no haya usuarios privados.
- mensaje premium se genera.
- endpoint admin de candidatos responde protegido.

## Nota de envío real

No se envió Telegram real desde el entorno local para evitar spam y porque los tests sustituyen la llamada HTTP por un fake sender. La certificación real debe hacerse en Render con un pick candidato real o un candidato de prueba controlado y revisando:

- `status=SENT`
- `sent_count=1`
- `last_cron_delivery_id` no vacío
- mensaje recibido en el canal.
