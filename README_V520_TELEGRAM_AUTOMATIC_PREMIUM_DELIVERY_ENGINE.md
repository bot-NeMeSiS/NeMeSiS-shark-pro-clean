# NeMeSiS SHARK PRO V520

## TELEGRAM AUTOMATIC PREMIUM DELIVERY ENGINE

Esta build convierte Telegram en un canal premium con control admin, cola, logs, reintentos y anti duplicados.

### Engine nuevo

- `engines/telegram_delivery_engine.py`

### Tablas nuevas o reforzadas

- `telegram_settings`
- `telegram_subscribers`
- `telegram_logs`
- `telegram_queue` ampliada con `chat_id`, `message_type`, `title`, `body`, `max_attempts`, `dedupe_key`, `scheduled_at`, `sent_at` y `error_message`.

### Rutas clave

- `/admin/telegram`
- `/api/telegram/diagnostics`
- `/api/telegram/settings`
- `/api/telegram/settings/update`
- `/api/telegram/send-test`
- `/api/telegram/enqueue-daily-matches`
- `/api/telegram/enqueue-daily-picks`
- `/api/telegram/process-queue`
- `/api/telegram/queue`
- `/api/telegram/logs`

Por defecto el envio automatico queda desactivado hasta que el administrador lo active. No se inventan picks ni partidos.
