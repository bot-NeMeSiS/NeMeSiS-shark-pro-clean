# V771 TELEGRAM ACTIVITY PRO FORMAT SCHEDULE FINAL

## Objetivo

Dejar Telegram como un canal vivo, premium y controlado, sin romper el flujo existente de Render Cron, cola, dedupe, picks, highlights, resultados, Madrid Time ni `DB_PATH=/data/database.db`.

## Cambios aplicados

- Versionado actualizado a `V771_TELEGRAM_ACTIVITY_PRO_FORMAT_SCHEDULE_FINAL`.
- Nuevo motor `engines/telegram_activity_engine.py` para decidir actividad por tick frecuente.
- Nuevo formateador `engines/telegram_message_formatter.py` para mensajes limpios en hora Madrid.
- Integracion de actividad V771 dentro de `telegram_scheduler_delivery()` sin sustituir el flujo anterior.
- Nuevos mensajes soportados:
  - resumen diario;
  - actualizacion de mediodia;
  - alerta live;
  - pick premium;
  - resultado final;
  - highlight/resumen disponible;
  - recordatorio prepartido;
  - cierre del dia.
- Dedupe separado por tipo, partido, pick, mercado, estado, fecha Madrid, modulo y destino.
- Quiet hours desactivable por entorno y desactivado por defecto para Mundial/partidos nocturnos.
- Override Mundial/top matches activo por defecto.
- Imagenes live desactivadas por defecto.
- Runner `tools/render_cron_telegram_tick.py` mejorado con log compacto: status, sent_count, modulos, dedupe/skipped, failed y hora Madrid.
- Panel `/admin/telegram/command-center` ampliado con seccion de actividad V771.
- Endpoints admin protegidos:
  - `/api/admin/telegram/activity-plan`
  - `/api/admin/telegram/schedule-status`
  - `/api/admin/telegram/message-preview`
  - `/api/admin/telegram/dedupe-status`

## Variables nuevas

Anadidas a `.env.example` y `.env.render.clean`:

- `TELEGRAM_ACTIVITY_LEVEL=medium_high`
- `TELEGRAM_QUIET_HOURS_ENABLED=false`
- `TELEGRAM_WORLD_CUP_OVERRIDE=true`
- `TELEGRAM_SEND_DAILY_SUMMARY=true`
- `TELEGRAM_SEND_LIVE_ALERTS=true`
- `TELEGRAM_SEND_PICK_ALERTS=true`
- `TELEGRAM_SEND_RESULT_ALERTS=true`
- `TELEGRAM_SEND_HIGHLIGHT_ALERTS=true`
- `TELEGRAM_SEND_PREMATCH_REMINDERS=true`
- `TELEGRAM_SEND_EVENING_RECAP=true`
- `TELEGRAM_SEND_LIVE_IMAGES=false`
- `TELEGRAM_CRON_INTERVAL_MINUTES=10`
- `TELEGRAM_DAILY_SUMMARY_TIME=09:00`
- `TELEGRAM_MIDDAY_UPDATE_TIME=13:30`
- `TELEGRAM_EVENING_RECAP_TIME=23:30`
- `TELEGRAM_PREMATCH_REMINDER_MINUTES=60`
- `TELEGRAM_MAX_ACTIVITY_MESSAGES_PER_TICK=6`

## Reglas preservadas

- No se toca `DB_PATH`.
- No se toca `AUTOMATION_SECRET`.
- No se cambia `/api/automation/telegram/tick`.
- No se elimina el runner `tools/render_cron_telegram_tick.py`.
- No se envia Telegram real en local.
- No se inventan partidos, picks, cuotas, resultados ni highlights.
- No se descargan ni rehostean videos.

## Resultado

Telegram queda preparado para actividad media-alta sin spam: un solo Cron frecuente llama al tick, la app decide internamente que mensajes tienen sentido, encola con dedupe y procesa la cola existente.

