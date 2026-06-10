# NeMeSiS SHARK PRO — V710 Render Cron Automation Final

Entrega limpia para GitHub + Render.

## Versión

`V710_RENDER_CRON_AUTOMATION_FINAL`

## Objetivo principal

Cerrar el bloqueo de Telegram automático en producción mediante Render Cron Jobs.

## Endpoints Cron

- `/api/automation/telegram/tick`
- `/api/automation/daily/run`

Comportamiento esperado:

- Sin secret: `403`
- Secret incorrecto: `403`
- Falta `AUTOMATION_SECRET`: `403 automation_secret_missing`
- Secret correcto: `200` con `cron: true`

## Variables importantes en Render

- `DB_PATH=/data/database.db`
- `SECRET_KEY=...`
- `THE_ODDS_API_KEY=...`
- `THESPORTSDB_API_KEY=...`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`
- `TELEGRAM_BOT_USERNAME=...`
- `AUTOMATION_SECRET=...`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`
- `RUN_DAILY_AUTOMATION=true`
- `RUN_STARTUP_SCHEDULER_NOW=0`

## Validación local realizada

- `python3 -m compileall -q app.py engines services blueprints` -> OK
- Cron smoke tests -> OK
- `pytest -q` -> 12 passed
- `python tools/smoke_check.py` -> OK con avisos legacy no bloqueantes

## Limpieza del ZIP

Este paquete no incluye `.git`, `.venv`, `__pycache__`, bases de datos locales, WAL/SHM, backups ni ZIPs anteriores.
