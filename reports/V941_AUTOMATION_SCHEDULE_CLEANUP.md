# V941 Automation Schedule Cleanup

## Objetivo
Un solo propietario para cada tarea recurrente. Evitar sincronizaciones dobles, gasto de API, Telegram duplicado y procesos heredados arrancando desde el web service.

## Tareas recurrentes que se mantienen
1. **Cron maestro** — cada 10 minutos.
   - Runner: `tools/render_cron_master_tick.py`
   - Incluye sincronización deportiva, cuotas, evaluación de pronósticos, Telegram y evolución segura.
   - El nombre Render `telegram-auto-tick` se conserva por compatibilidad para no crear accidentalmente un segundo servicio al renombrarlo.

2. **Backup diario** — `30 2 * * *` en Render.
   - Runner: `tools/render_cron_data_backup.py`
   - Render interpreta el cron en UTC: 02:30 UTC = 03:30/04:30 Madrid según época.
   - La copia se crea en el web service, que es quien tiene el disco persistente y `DB_PATH=/data/database.db`.

## Capacidades que quedan manuales o incluidas
- scheduler_engine heredado: manual/compatibilidad, OFF por defecto.
- Daily Automation V818: manual/diagnóstico.
- Sports sync separado: incluido en cron maestro.
- Pick grading separado: incluido en cron maestro.
- Highlights sync: bajo demanda.
- Sentinel scans: QA/diagnóstico bajo demanda.
- Browser/Visual QA: CI o ejecución manual.
- Workers históricos: herramientas internas, no crons de producción.

## Guardrails
- `SCHEDULER_ENABLED=0`
- `ENABLE_AUTO_SYNC=0`
- `AUTO_SYNC_ON_STARTUP=0`
- `DAILY_AUTOMATION_ENABLED=0`
- Default de `scheduler_env_enabled()`: OFF si faltan variables.
- Arranque del scheduler heredado requiere además `RUN_STARTUP_SCHEDULER_NOW=1`.
- Regla Reliability: `ONE_RECURRING_OWNER -> NO_DUPLICATE_SCHEDULERS`.

## Estado externo
Este inventario describe la candidata Git/Render Blueprint. No afirma que servicios cron antiguos creados manualmente en el Dashboard de Render hayan sido eliminados. Esa comprobación requiere revisar el workspace real de Render de forma explícitamente autorizada.
