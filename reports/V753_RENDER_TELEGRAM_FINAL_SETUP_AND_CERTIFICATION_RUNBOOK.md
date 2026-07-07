# V753 Render Telegram Final Setup and Certification Runbook

## Web Service Environment

Configurar en el Web Service:

```env
AUTOMATION_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_BOT_USERNAME=...
ENABLE_TELEGRAM_AUTO=true
AUTO_SEND_TELEGRAM_PICKS=true
TELEGRAM_AUTO_SEND_ENABLED=true
ENABLE_TELEGRAM_AUTOMATION=true
AUTO_GENERATE_PICKS=true
TZ=Europe/Madrid
APP_TIMEZONE=Europe/Madrid
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
```

## Cron Job Environment

Configurar en el Cron Job:

```env
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=***hidden***
```

## Cron Command

```bash
python tools/render_cron_telegram_tick.py
```

## Qué registra V753

Cuando el runner real llama al endpoint, el sistema guarda:

- `cron_runner_detected=true`,
- `last_cron_runner_at`,
- `last_cron_http_status`,
- `last_cron_result`,
- `last_cron_source=automatic_cron`,
- `last_cron_sent_count`,
- `last_cron_delivery_id`,
- `last_cron_madrid_time`,
- `last_cron_utc_time`.

## Cómo certificar

1. Desplegar V753.
2. Abrir `/api/runtime-version` y confirmar versión V753.
3. En Render, abrir el Cron Job.
4. Pulsar `Trigger Run`.
5. Ver en logs `CRON_TICK_START`.
6. Ver en logs `CRON_TICK_RESPONSE`.
7. Confirmar HTTP 200.
8. Abrir `/admin/telegram/command-center`.
9. Confirmar `Cron real detectado: Sí`.
10. Confirmar `Último tick Cron`.
11. Confirmar `Último resultado Cron`.

## Interpretación

- `NO_DUE_JOBS`: correcto. Cron funciona, no había nada pendiente.
- `NO_ELIGIBLE_PICKS`: correcto. No había pick válido para enviar.
- `OUTSIDE_PRO_WINDOW`: correcto. El sistema respetó ventana profesional.
- `DUPLICATE_ALREADY_SENT`: correcto. Dedupe evitó spam.
- `SENT`: enviado. Confirmar `sent_count>0`, `last_delivery_id` y mensaje en Telegram.
- 403: `AUTOMATION_SECRET` del Cron no coincide con el Web Service.

## Separación de fuentes

- Manual admin: `source=manual_admin`, `trigger_type=admin_button`.
- Preview/dry-run: `source=admin_preview`, `trigger_type=dry_run`, `sent=false`.
- Simulación admin: no certifica Render Cron.
- Cron real: `source=automatic_cron`, `trigger_type=render_cron`, `cron_runner_detected=true`.

## Si el manual funciona pero el automático no

Revisar en este orden:

1. `Cron real detectado`.
2. `AUTOMATION_SECRET`.
3. Los cuatro flags oficiales.
4. `TELEGRAM_CHAT_ID`.
5. Motivos de descarte.
6. Dedupe.
7. Ventana profesional.
8. Existencia de picks candidatos.

