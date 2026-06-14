# V771 RENDER CRON ACTIVITY RUNBOOK

## Cron recomendado

Un solo Cron Job:

- Nombre: `NeMeSiS Telegram Activity Tick`
- Frecuencia recomendada: `*/10 * * * *`
- Frecuencia alternativa: `*/15 * * * *`
- Comando: `python tools/render_cron_telegram_tick.py`

## Variables necesarias en Render Cron

- `PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com`
- `AUTOMATION_SECRET=<mismo valor que en el Web Service>`

## Variables necesarias en Web Service

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `ENABLE_TELEGRAM_AUTOMATION=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `TELEGRAM_AUTO_SEND_ENABLED=true`
- `TELEGRAM_ACTIVITY_LEVEL=medium_high`
- `TELEGRAM_QUIET_HOURS_ENABLED=false`
- `TELEGRAM_WORLD_CUP_OVERRIDE=true`
- `TELEGRAM_CRON_INTERVAL_MINUTES=10`

## Que hace cada tick

1. Render ejecuta el runner.
2. El runner llama a `/api/automation/telegram/tick?secret=...&runner=render_cron`.
3. La app valida `AUTOMATION_SECRET`.
4. La app revisa picks automaticos existentes.
5. La app construye actividad V771: resumen, live, picks, resultados, highlights, recordatorios y cierre.
6. La app encola solo mensajes reales.
7. La cola procesa mensajes pendientes.
8. El dedupe evita duplicados.
9. El panel admin muestra estado, candidatos y bloqueadores.

## Estados esperados

- `SENT`: se envio algun mensaje.
- `QUEUED`: se encolo mensaje para procesar.
- `DUPLICATE_ALREADY_SENT`: el dedupe evito repetir.
- `NO_ACTIVITY_CANDIDATES`: no habia contenido real que enviar.
- `NO_ELIGIBLE_PICKS`: no habia picks con cuota/mercado/riesgo validos.
- `NO_DESTINATION`: falta canal o usuarios vinculados.

## Importante

No crear muchos Cron Jobs. V771 esta disenado para un solo tick frecuente y decision interna.

