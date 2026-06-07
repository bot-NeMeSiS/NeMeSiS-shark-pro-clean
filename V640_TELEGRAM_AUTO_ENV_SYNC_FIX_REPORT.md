# V640 TELEGRAM AUTO ENV SYNC FIX

## Causa raíz

El envío manual de Telegram funcionaba, pero el automático podía abortar porque `telegram_settings.enabled` quedaba guardado como `0` en SQLite. Las rutas automáticas consultaban la BD antes de enviar y no respetaban suficientemente `ENABLE_TELEGRAM_AUTO=true` / `AUTO_SEND_TELEGRAM_PICKS=true` de Render.

## Corrección aplicada

- `get_telegram_settings()` ahora hace heal-on-read: si existen `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y Telegram auto está activo por env vars, sincroniza `enabled=1` y `auto_daily_picks=1` en BD.
- Añadida `_telegram_sync_env_on_startup()` para sincronizar la configuración al arrancar cuando proceda.
- `telegram_config()`, `process_premium_telegram_queue()`, `telegram_scheduler_delivery()` y `telegram_scheduler_tick()` respetan el estado efectivo env+BD.
- `/admin/telegram/diagnostics` expone `effective_enabled`, `env_auto_enabled` y `env_ready`.
- `.env.example` y `env.example` documentan `TELEGRAM_BOT_USERNAME` y `AUTO_SEND_TELEGRAM_PICKS`.

## Variables Render necesarias

```env
TELEGRAM_BOT_TOKEN=tu_token
TELEGRAM_CHAT_ID=tu_chat_id
TELEGRAM_BOT_USERNAME=nemesi_shark_pro_bot
ENABLE_TELEGRAM_AUTO=true
AUTO_SEND_TELEGRAM_PICKS=true
```

## Validación

- `python -m compileall app.py engines database_manager.py services`: OK.
- Import Flask con DB temporal: OK.
- `get_telegram_settings()` con env vars activa BD: OK.
- `/api/health`: OK.
- `/admin/telegram/diagnostics` autenticado: OK.

## Nota

El envío real a Telegram depende de Render y de la API real de Telegram. Esta versión deja corregido el bloqueo lógico que apagaba el automático desde la BD.
