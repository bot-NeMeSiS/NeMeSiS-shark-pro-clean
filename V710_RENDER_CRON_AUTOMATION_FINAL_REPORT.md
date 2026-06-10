# V710 Render Cron Automation Final Report

## Objetivo

Cerrar el sistema de Telegram automático en producción mediante Render Cron, sin más cambios de Telegram, SHARK ni Picks.

## Veredicto Final

El código está preparado para automatización real.

Para que funcione sin intervención del administrador, Render debe ejecutar dos Cron Jobs externos:

- Telegram Scheduler cada 15 minutos.
- Daily Automation cada hora o diario a las 10:00 Europe/Madrid.

Sin Render Cron, el Web Service no garantiza ejecución autónoma.

## Endpoints Certificados

### `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`

- Existe: sí.
- Método: GET o POST.
- Sin secreto: devuelve 403.
- Con secreto válido: devuelve 200.
- Registra `last_cron_telegram_call`.
- Ejecuta `telegram_scheduler_tick()`.
- Procesa cola Telegram.
- Usa dedupe para evitar duplicados.
- No requiere que el admin entre al panel.

### `/api/automation/daily/run?secret=AUTOMATION_SECRET`

- Existe: sí.
- Método: GET o POST.
- Sin secreto: devuelve 403.
- Con secreto válido: devuelve 200.
- Registra `last_cron_daily_call`.
- Ejecuta `run_daily_autonomous_system()`.
- Actualiza partidos, live, recomendaciones, auto picks, Telegram y backup.
- No requiere que el admin entre al panel.

## Variables Render Obligatorias

La app necesita:

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`

También debe mantenerse:

- `DB_PATH=/data/database.db`

## Diagnóstico Admin

`/admin/telegram/diagnostics` debe mostrar:

- `last_cron_telegram_call`
- `last_cron_daily_call`
- `last_auto_pick`
- `last_sent`
- `pending`
- `sent_today`
- `failed_today`
- `automatic_status`
- `chat_id_present`
- `env_flags.AUTOMATION_SECRET`

## Prueba Local Ejecutada

Con base temporal y secreto de prueba:

- `/api/automation/telegram/tick` sin secreto: 403.
- `/api/automation/telegram/tick?secret=...` con secreto: 200.
- `/api/automation/daily/run` sin secreto: 403.
- `/api/automation/daily/run?secret=...` con secreto: 200.
- `last_cron_telegram_call`: registrado.
- `last_cron_daily_call`: registrado.
- cola procesada: sí.
- la web no se rompe: sí.

La prueba local usó envío simulado para no mandar mensajes reales desde el entorno de desarrollo.

## Resultado

Después de configurar Render Cron:

El admin no tiene que pulsar nada.

Render llama automáticamente a los endpoints.

NeMeSiS puede generar picks, procesar cola y enviar Telegram automáticamente.

Telegram automático queda cerrado de forma real en producción cuando los Cron Jobs estén creados en Render.

