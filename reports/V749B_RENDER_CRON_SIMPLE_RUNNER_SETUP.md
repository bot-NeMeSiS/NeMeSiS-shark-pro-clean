# V749B Render Cron Simple Runner Setup

## Objetivo

Esta versión evita el problema de comandos `curl` con comillas rotas en Render Cron. El Cron Job ya no necesita pegar URLs largas ni secrets dentro del campo **Command**.

El comando final debe ser solamente:

```bash
python tools/render_cron_telegram_tick.py
```

## Configuración del Cron Job en Render

Crea un Cron Job nuevo con estos valores:

- **Name:** `telegram-auto-tick`
- **Build Command:** `pip install -r requirements.txt`
- **Schedule:** `*/5 * * * *`
- **Command:** `python tools/render_cron_telegram_tick.py`

## Environment del Cron Job

El Cron Job solo necesita estas dos variables:

```env
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=***hidden***
```

No pongas el secret dentro del Command. No uses `curl`. No pegues la URL larga en el Command.

## Variables que deben estar en el Web Service principal

El Web Service principal debe conservar sus variables reales:

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

No cambies `DB_PATH` si producción ya guarda usuarios y datos correctamente.

## Cómo interpretar logs del runner

- HTTP `200`: el Cron llega a la app. Puede devolver `NO_DUE_JOBS` y seguir siendo correcto.
- HTTP `403`: `AUTOMATION_SECRET` del Cron no coincide con el Web Service.
- `MISSING_PUBLIC_BASE_URL`: falta `PUBLIC_BASE_URL` en el Cron Job.
- `MISSING_AUTOMATION_SECRET`: falta `AUTOMATION_SECRET` en el Cron Job.
- `CRON_TICK_NETWORK_ERROR`: la app no respondió o hubo error de red.

## Cómo confirmar que funciona

1. Guarda el Cron Job.
2. Espera una ejecución o lanza Manual Run.
3. En los logs del Cron debe aparecer `CRON_TICK_RESPONSE` con `status: 200`.
4. Entra en `/admin/telegram/command-center`.
5. Confirma que aparece `last_automation_tick` o fuente `automatic_cron` actualizada.

## Regla de seguridad

El runner enmascara el secret en logs como `***abcd`. Nunca debe imprimir el valor completo.
