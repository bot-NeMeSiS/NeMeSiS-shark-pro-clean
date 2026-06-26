# V853 Admin Telegram Command Center QA

Telegram V844 se conserva.

Validado por estructura:
- `engines/telegram_quality_filter_engine.py` sigue existiendo.
- `/admin/telegram/command-center` sigue enlazado desde el command strip.
- El dashboard admin corrige el texto de diagnósticos.

V853 no envía Telegram real en local. La capa visual no modifica dedupe, filtros top, no-filler ni cron.
