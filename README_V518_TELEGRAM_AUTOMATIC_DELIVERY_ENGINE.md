# NeMeSiS SHARK PRO V518 — Telegram Automatic Delivery Engine

Versión completa Render-ready basada en V517.

## Incluye
- Scheduler Telegram persistente.
- Cola de envíos `telegram_queue`.
- Logs en `telegram_deliveries`.
- Anti duplicados por firma diaria.
- Retry básico.
- Auto posts preparados desde live, picks y partidos destacados.
- Panel admin protegido `/admin/telegram`.
- APIs:
  - `/api/telegram/status`
  - `/api/telegram/queue`
  - `/api/telegram/logs`
  - `/api/telegram/triggers`
  - `/api/telegram/scheduler-tick`
  - `/api/telegram/scheduler-manager`
  - `/api/telegram/auto-posts`
- Mantiene login, registro, admin bootstrap, recuperación usuarios, favoritos por usuario y SportsDB.

## Variables Render recomendadas
```txt
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
ENABLE_TELEGRAM_AUTO=true
TELEGRAM_AUTO_MINUTES=360
```

## QA básico
- `python -m py_compile app.py engines/*.py`
- `/api/health`
- `/admin/telegram`
- `/api/telegram/status`
- `/api/telegram/scheduler-tick?force=1`

## Commit recomendado
```txt
V518 TELEGRAM AUTOMATIC DELIVERY ENGINE
```
