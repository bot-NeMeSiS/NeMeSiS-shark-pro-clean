# V753 Telegram Production Autopilot Environment Audit

## Objetivo

Eliminar la confusión entre envío manual, preview, simulación de admin y Cron real de Render. A partir de V753, el Command Center debe permitir saber:

- si Render Cron está llamando,
- si Telegram está listo,
- si el automático está realmente activo,
- si hay candidatos,
- si no envía, por qué no envía,
- si envía, qué `delivery_id` dejó.

## Cambios aplicados

- Versión actualizada a `V753_TELEGRAM_PRODUCTION_AUTOPILOT_ENVIRONMENT_AUDIT_AND_REAL_CRON_CERTIFICATION`.
- Nuevo engine `engines/telegram_environment_engine.py`.
- Nueva función central `get_telegram_environment_audit()`.
- Nueva función central `is_telegram_auto_enabled()`.
- Nuevo endpoint protegido: `/api/admin/telegram/environment-audit`.
- El runner `tools/render_cron_telegram_tick.py` ahora manda:
  - header `X-NeMeSiS-Cron-Runner: render-cron`,
  - query `runner=render_cron`.
- El endpoint `/api/automation/telegram/tick` guarda evidencia:
  - `last_automation_tick`,
  - `last_cron_runner_at`,
  - `last_cron_http_status`,
  - `last_cron_result`,
  - `last_cron_source=automatic_cron`,
  - `last_cron_sent_count`,
  - `last_cron_delivery_id`,
  - `last_cron_madrid_time`,
  - `last_cron_utc_time`.
- Los mensajes automáticos encolados desde el flujo de Telegram usan:
  - `source=automatic_cron`,
  - `trigger_type=render_cron`,
  - `job_type=auto_pick`, `daily_picks`, `daily_matches` o `live_alert`.
- Los botones manuales admin usan:
  - `source=manual_admin`,
  - `trigger_type=admin_button`.
- El dry-run/preview devuelve:
  - `source=admin_preview`,
  - `trigger_type=dry_run`,
  - `sent=false`.
- El Command Center muestra bloque de Environment V753, Cron real detectado, separación de fuentes, últimos contadores y motivos de descarte.

## Flags oficiales

V753 considera Telegram automático activo solo si están en true:

- `ENABLE_TELEGRAM_AUTO`
- `AUTO_SEND_TELEGRAM_PICKS`
- `TELEGRAM_AUTO_SEND_ENABLED`
- `ENABLE_TELEGRAM_AUTOMATION`

Las variables legacy pueden seguir existiendo, pero no sustituyen a estos cuatro flags.

## Estados sanos

- `NO_DUE_JOBS`: Cron funciona, no tocaba enviar.
- `QUEUE_EMPTY`: cola vacía.
- `NO_ELIGIBLE_PICKS`: no hay pick válido.
- `OUTSIDE_PRO_WINDOW`: fuera de ventana profesional.
- `NO_LIVE_ALERTS`: no hay alerta live real.
- `DUPLICATE_ALREADY_SENT`: dedupe evitó spam.

## Estados problemáticos

- `AUTO_DISABLED`
- `TELEGRAM_NOT_READY`
- `MISSING_BOT_TOKEN`
- `MISSING_CHAT_ID`
- `NO_DESTINATION`
- `HTML_PARSE_ERROR`
- `NETWORK_ERROR`
- `RATE_LIMIT`

## Validación local

Se añadió `tools/check_v753_telegram_production_autopilot.py`.

La prueba usa DB temporal y mock de `telegram_send_http`, por lo que no envía Telegram real.

Valida:

- endpoint sin secret 403,
- endpoint con secret y runner 200,
- `cron_runner_detected=true`,
- environment audit OK,
- pick futuro válido,
- auto-pick encolado,
- envío mock `sent=1`,
- `source=automatic_cron`,
- `trigger_type=render_cron`,
- `delivery_id` existente,
- mensaje premium con Madrid Time,
- segundo tick `DUPLICATE_ALREADY_SENT`,
- prueba manual separada como `manual_admin/admin_button`.

## Limitación honesta

No se envió un mensaje real para evitar spam. La prueba final en Render debe confirmar `status=SENT`, `sent_count>0`, `last_delivery_id` y mensaje recibido cuando exista un candidato real.

