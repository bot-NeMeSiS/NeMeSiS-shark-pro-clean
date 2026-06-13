# V754 Telegram Real Send Certification Runbook

## Objetivo

Certificar en Render que el flujo real queda cerrado:

Render Cron -> `/api/automation/telegram/tick` -> candidato auto pick -> cola -> Telegram -> `SENT`.

## Variables necesarias

En el Web Service:

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `ENABLE_TELEGRAM_AUTOMATION=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `TELEGRAM_AUTO_SEND_ENABLED=true`
- `AUTO_GENERATE_PICKS=true`
- `TZ=Europe/Madrid`
- `APP_TIMEZONE=Europe/Madrid`
- `PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com`

Variables V754 opcionales con defaults seguros:

- `TELEGRAM_PICK_SEND_WINDOW_HOURS_BEFORE=24`
- `TELEGRAM_PICK_SEND_MIN_MINUTES_BEFORE=15`
- `TELEGRAM_SUMMARY_MORNING_WINDOW=09:00-11:30`
- `TELEGRAM_SUMMARY_EVENING_WINDOW=17:00-19:30`
- `TELEGRAM_AUTO_PICK_RESPECT_QUIET_HOURS=false`

En el Cron Job:

- `PUBLIC_BASE_URL`
- `AUTOMATION_SECRET`

## Comando Render Cron

Mantener:

```bash
python tools/render_cron_telegram_tick.py
```

El runner debe enviar:

- Header `X-NeMeSiS-Cron-Runner: render-cron`
- Query `runner=render_cron`

## Certificación paso a paso

1. Abrir `/admin/telegram/command-center`.
2. Confirmar:
   - Cron real detectado: Sí.
   - Telegram ready: Sí.
   - Auto Telegram: ON.
   - `AUTOMATION_SECRET`: configurado.
3. Abrir `/api/admin/telegram/auto-candidates` como admin.
4. Revisar:
   - `reviewed`
   - `candidates`
   - `eligible`
   - `next_candidate`
   - `discarded`
5. Si `eligible=0`, revisar el motivo:
   - `OLD_MATCH`: el partido ya empezó o pasó.
   - `MISSING_MATCH_TIME`: falta hora suficiente.
   - `TOO_EARLY`: el partido está fuera de la ventana previa.
   - `TOO_LATE`: queda menos del mínimo antes de inicio.
   - `DUPLICATE_ALREADY_SENT`: ya se envió ese pick para ese destino.
   - `NO_DESTINATION`: falta canal global o destinos privados.
6. Hacer Trigger Run en Render Cron.
7. Esperar respuesta 200.
8. Confirmar en respuesta:
   - `cron_runner_detected=true`
   - `cron_status=CRON_OK`
   - `modules.auto_picks.status=SENT` si había candidato.
   - `sent_count=1`
   - `last_cron_delivery_id` no vacío.
9. Confirmar que el mensaje llega al canal.

## Resultado correcto con candidato válido

```json
{
  "cron_runner_detected": true,
  "cron_status": "CRON_OK",
  "last_cron_source": "automatic_cron",
  "status": "SENT",
  "sent_count": 1,
  "last_cron_delivery_id": "..."
}
```

## Si no envía

No asumir fallo de Telegram si `/api/telegram/send` funciona.

Revisar primero:

- `/api/admin/telegram/auto-candidates`
- `modules.auto_picks.status`
- `discard_reasons`
- dedupe del candidato
- ventana Madrid del partido

## Qué no debe hacerse

- No cambiar el runner si `cron_runner_detected=true`.
- No tocar `TELEGRAM_BOT_TOKEN` ni `TELEGRAM_CHAT_ID` si manual funciona.
- No forzar picks viejos.
- No borrar historial de dedupe salvo revisión manual.
- No activar spam para saltarse límites.
