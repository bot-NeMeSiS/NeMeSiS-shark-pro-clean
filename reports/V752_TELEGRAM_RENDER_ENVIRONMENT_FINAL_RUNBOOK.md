# V752 Telegram Render Environment Final Runbook

## Web Service: variables obligatorias

Configurar en el Web Service de Render:

```env
AUTOMATION_SECRET=***hidden***
TELEGRAM_BOT_TOKEN=***hidden***
TELEGRAM_CHAT_ID=chat_o_canal_global
TELEGRAM_BOT_USERNAME=nombre_del_bot
ENABLE_TELEGRAM_AUTO=true
AUTO_SEND_TELEGRAM_PICKS=true
TELEGRAM_AUTO_SEND_ENABLED=true
ENABLE_TELEGRAM_AUTOMATION=true
AUTO_GENERATE_PICKS=true
TZ=Europe/Madrid
APP_TIMEZONE=Europe/Madrid
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
```

No exponer estos valores en capturas públicas. El panel solo muestra presencia, nunca secrets completos.

## Cron Job: variables obligatorias

Configurar en el Cron Job de Render:

```env
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=***hidden***
```

## Cron Job recomendado

Nombre:

`NeMeSiS Telegram Tick`

Command:

```bash
python tools/render_cron_telegram_tick.py
```

Frecuencia:

Cada 15 minutos.

## Qué hace el runner

`tools/render_cron_telegram_tick.py`:

- lee `PUBLIC_BASE_URL`,
- lee `AUTOMATION_SECRET`,
- llama a `/api/automation/telegram/tick?secret=...`,
- imprime JSON con HTTP status,
- muestra hora UTC y hora Madrid,
- oculta el secret completo,
- sale `0` si HTTP 200,
- sale `3` si HTTP 403,
- sale `2` si faltan variables,
- sale `4` si hay error de red.

## Interpretación de respuestas

### 200 con `NO_DUE_JOBS`

Correcto. El Cron funciona, el secret funciona y no había trabajo pendiente.

### 200 con `QUEUE_EMPTY`

Correcto. La cola estaba vacía.

### 200 con `NO_ELIGIBLE_PICKS`

Correcto. SHARK revisó candidatos, pero no había picks válidos para enviar.

### 200 con `OUTSIDE_PRO_WINDOW`

Correcto. El sistema respetó la ventana profesional.

### 200 con `SENT`

Correcto. Hubo envío real. Confirmar:

- `sent_count > 0`,
- `last_delivery_id`,
- mensaje recibido en Telegram.

### 403

Fallo de configuración. `AUTOMATION_SECRET` del Cron Job no coincide con el Web Service o falta en la URL.

### `TELEGRAM_NOT_READY`, `MISSING_BOT_TOKEN`, `MISSING_CHAT_ID`

Falta configuración Telegram real en el Web Service.

## Cómo probar Trigger Run

1. Abrir Render Dashboard.
2. Entrar en el Cron Job `NeMeSiS Telegram Tick`.
3. Pulsar `Trigger Run`.
4. Revisar logs del Cron.
5. Buscar `CRON_TICK_RESPONSE`.
6. Confirmar HTTP `200`.
7. Entrar en `/admin/telegram/command-center`.
8. Confirmar `último tick automático`, `último resultado tick`, `discard_reasons` y `next_run_madrid`.

## Confirmación final de envío automático

Telegram automático queda cerrado a nivel código cuando:

- Render Cron devuelve 200,
- `automation_enabled=true`,
- `telegram_ready=true`,
- hay pick candidato elegible,
- el endpoint devuelve `status=SENT`,
- `sent_count > 0`,
- se ve `last_delivery_id`,
- el canal o privado recibe el mensaje.

Si el resultado es `NO_DUE_JOBS`, `QUEUE_EMPTY` o `NO_ELIGIBLE_PICKS`, no es fallo: falta un candidato real o ventana de envío.

