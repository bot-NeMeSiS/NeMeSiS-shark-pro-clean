# V749B_RENDER_CRON_SIMPLE_RUNNER_FINAL_FIX_REPORT

## Resumen

Se creó una mini versión de continuidad sobre V749 para simplificar al máximo la configuración de Render Cron. El problema detectado en producción no era Telegram ni el endpoint automático, sino el comando del Cron Job con `curl` y comillas/secrets mal cerrados, que producía errores tipo `unexpected EOF` antes de llegar a la app.

## Cambio principal

Nuevo runner:

```bash
python tools/render_cron_telegram_tick.py
```

Este script llama al endpoint ya existente:

```text
/api/automation/telegram/tick
```

leyendo solo:

```env
PUBLIC_BASE_URL
AUTOMATION_SECRET
```

## Por qué mejora el sistema

- No requiere `curl`.
- No requiere pegar secrets en el Command.
- Evita errores de shell y comillas.
- Usa solo librería estándar Python.
- Imprime logs claros con hora UTC y hora Madrid.
- Enmascara el secret.
- Devuelve códigos de salida claros para Render.

## Command exacto para Render Cron

```bash
python tools/render_cron_telegram_tick.py
```

## Environment exacto del Cron Job

```env
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=***hidden***
```

## Schedule recomendado

```cron
*/5 * * * *
```

## Variables que se quedan en el Web Service

```env
AUTOMATION_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
ENABLE_TELEGRAM_AUTO=true
AUTO_SEND_TELEGRAM_PICKS=true
TELEGRAM_AUTO_SEND_ENABLED=true
ENABLE_TELEGRAM_AUTOMATION=true
TZ=Europe/Madrid
APP_TIMEZONE=Europe/Madrid
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
```

## Validación esperada en Render

- `200` o `NO_DUE_JOBS`: el Cron funciona.
- `403`: secret incorrecto o diferente.
- `last_automation_tick` actualizado en Command Center: Render Cron está llegando.
- `sent_count > 0`: Telegram automático envió algo.
- `DUPLICATE_ALREADY_SENT`: dedupe evita spam.

## Archivos añadidos/tocados

- `VERSION.txt`
- `tools/render_cron_telegram_tick.py`
- `tools/check_v749b_render_cron_simple_runner.py`
- `tools/check_v749_telegram_auto_delivery_madrid_time.py`
- `tools/build_clean_release.py`
- `reports/V749B_RENDER_CRON_SIMPLE_RUNNER_SETUP.md`
- `reports/V749B_RENDER_CRON_SIMPLE_RUNNER_FINAL_FIX_REPORT.md`

## Nota honesta

No se ha enviado Telegram real desde esta preparación. La certificación real final es crear el Cron Job con el command simple, ejecutar el runner en Render y confirmar que el panel muestra `last_automation_tick` actualizado.
