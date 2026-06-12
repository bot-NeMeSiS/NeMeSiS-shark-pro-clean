# Telegram Automation Render Setup V742

Esta guía no contiene secrets reales.

## Variables Render necesarias

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`

## Cron 1: Telegram Tick

- Nombre: `NeMeSiS Telegram Tick`
- Frecuencia: cada 15 minutos.
- Método: `GET`
- URL: `https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_DE_AUTOMATION_SECRET`
- Objetivo: procesar cola Telegram, picks automáticos, dedupe y envíos.

## Cron 2: Daily Automation

- Nombre: `NeMeSiS Daily Automation`
- Frecuencia: cada hora o diario a las 10:00 Europe/Madrid.
- Método: `GET`
- URL: `https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_DE_AUTOMATION_SECRET`
- Objetivo: actualizar partidos, picks, recomendaciones, Telegram y backups.

## Pruebas seguras

- Sin `secret`, ambos endpoints deben devolver `403`.
- Con `secret`, ambos endpoints deben devolver `200` con JSON.
- Revisar `/admin/telegram/command-center`.
- Revisar `/api/admin/telegram/status` con sesión admin.

## Si no envía

- `MISSING_BOT_TOKEN`: falta token en Render.
- `MISSING_CHAT_ID`: falta destino/canal.
- `BOT_NOT_IN_GROUP_OR_CHANNEL`: el bot no está en el grupo/canal o fue expulsado.
- `BOT_NOT_ADMIN_IN_CHANNEL`: el bot no tiene permisos suficientes.
- `BLOCKED_BY_QUIET_HOURS`: horario silencioso activo.
- `ALL_ALREADY_SENT`: dedupe evita duplicado real.
- `NO_PREMIUM_PICKS`: no hay picks válidos para enviar.

No hacer test-send masivo. Usar dry-run y preview antes de cualquier prueba real.
