# V710 Telegram Auto Send Via Render Cron Report

## Objetivo

Dejar cerrado el envío automático de picks a Telegram mediante Render Cron, sin intervención del administrador.

## Veredicto

El sistema está preparado para producción mediante Render Cron.

Telegram automático queda cerrado cuando Render ejecute estos endpoints con `AUTOMATION_SECRET`:

- `/api/automation/telegram/tick`
- `/api/automation/daily/run`

## Endpoints Certificados

### `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`

- Existe: sí.
- Método: GET o POST.
- Sin secreto: 403.
- Con secreto válido: 200.
- No depende de sesión admin.
- No depende de request de usuario.
- Procesa cola Telegram.
- Actualiza `last_cron_telegram_call`.
- Evita duplicados mediante `dedupe_key`.

### `/api/automation/daily/run?secret=AUTOMATION_SECRET`

- Existe: sí.
- Método: GET o POST.
- Sin secreto: 403.
- Con secreto válido: 200.
- No depende de sesión admin.
- No depende de request de usuario.
- Ejecuta automatización diaria.
- Actualiza `last_cron_daily_call`.
- Puede generar/actualizar recomendaciones, picks, Telegram y backups.

## Variables Render Soportadas

La aplicación lee y usa:

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO`
- `AUTO_SEND_TELEGRAM_PICKS`
- `AUTO_GENERATE_PICKS`
- `SCHEDULER_ENABLED`
- `DAILY_AUTOMATION_ENABLED`

Valores recomendados:

- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`

## Diagnóstico Admin

`/admin/telegram/diagnostics` muestra:

- último cron telegram: `last_cron_telegram_call`.
- último cron daily: `last_cron_daily_call`.
- automático activo: `automatic_status`.
- canal configurado: `chat_id_present`.
- secret configurado: `env_flags.AUTOMATION_SECRET`.
- último auto pick: `last_auto_pick`.
- último envío Telegram: `last_sent`.
- cola pendiente: `pending`.
- enviados hoy: `sent_today`.
- fallidos hoy: `failed_today`.
- último error: `last_error`.

## Prueba Final Local

Se ejecutó una llamada Cron simulada con secreto válido y envío Telegram simulado para no mandar mensajes reales desde desarrollo.

Resultado:

- Telegram Tick sin secreto: 403.
- Telegram Tick con secreto: 200.
- Estado Telegram Tick: `QUEUE_PROCESSED`.
- Mensajes enviados por la cola: 2.
- Daily Automation sin secreto: 403.
- Daily Automation con secreto: 200.
- `last_cron_telegram_call`: actualizado.
- `last_cron_daily_call`: actualizado.
- cola pendiente: 0.
- enviados hoy: 2.
- fallidos hoy: 0.
- dedupe activo: duplicado omitido.
- observability errors: 0.

## Conclusión

Después de crear los Cron Jobs en Render:

- el admin no toca nada.
- Render llama automáticamente.
- NeMeSiS genera picks.
- NeMeSiS procesa cola.
- Telegram recibe mensajes automáticamente.
- los duplicados se evitan.

Telegram automático queda cerrado de forma real con Render Cron activo.

