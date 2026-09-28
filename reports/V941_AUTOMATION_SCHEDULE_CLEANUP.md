# V941 Automation Schedule Cleanup

## Objetivo
Un solo propietario para toda recurrencia de producción. Evitar sincronizaciones dobles, gasto de API, Telegram duplicado y procesos heredados arrancando desde el web service.

## Única tarea recurrente
**Cron maestro — cada 10 minutos**
- Servicio Render histórico: `telegram-auto-tick` (nombre conservado para evitar crear un segundo servicio al renombrar).
- Runner: `tools/render_cron_master_tick.py`.
- Incluye sincronización deportiva, cuotas, evaluación de pronósticos, Telegram, evolución segura y backup diario.
- Backup: ventana 02:30–04:30 UTC; el web service usa claim temporal atómico y memoria del último backup exitoso para crear como máximo una copia diaria.
- El runner de backup independiente se conserva como herramienta manual/emergencia, pero no está programado en `render.yaml`.

## Capacidades manuales o incluidas
- scheduler_engine heredado: manual/compatibilidad, OFF por defecto.
- Daily Automation V818: manual/diagnóstico.
- Sports sync separado: incluido en cron maestro.
- Pick grading separado: incluido en cron maestro.
- Highlights sync: bajo demanda.
- Sentinel scans: QA/diagnóstico bajo demanda.
- Browser/Visual QA: CI o ejecución manual.
- Workers históricos: herramientas internas, no crons de producción.

## Guardrails
- `render.yaml` contiene exactamente un `type: cron`.
- `SCHEDULER_ENABLED=0`.
- `ENABLE_AUTO_SYNC=0`.
- `AUTO_SYNC_ON_STARTUP=0`.
- `DAILY_AUTOMATION_ENABLED=0`.
- Default de `scheduler_env_enabled()`: OFF si faltan variables.
- Arranque del scheduler heredado requiere además `RUN_STARTUP_SCHEDULER_NOW=1`.
- `DATA_BACKUP_ENABLED=1` vive en el web service que posee `/data`.
- Regla Reliability: `ONE_RECURRING_OWNER -> NO_DUPLICATE_SCHEDULERS`.

## Estado externo
Este inventario describe la candidata Git/Render Blueprint. No afirma que servicios cron antiguos creados manualmente en el Dashboard de Render hayan sido eliminados. Esa comprobación requiere revisar el workspace real de Render de forma explícitamente autorizada.
