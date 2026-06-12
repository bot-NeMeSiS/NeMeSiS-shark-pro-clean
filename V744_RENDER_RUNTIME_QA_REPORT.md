# V744 Render Runtime QA

## Verificaciones

- Runtime ultraligero en `/api/runtime-version`.
- Estado de cron visible.
- Estado Telegram visible sin exponer secrets.
- Estado backup visible.
- No se lanzan procesos pesados desde runtime.

## Riesgos controlados

- Si falta `AUTOMATION_SECRET`, los cron quedan protegidos y devuelven error claro.
- Si falta Telegram, la web no se rompe.
- Si `DATA_BACKUP_ENABLED=false`, backup cron no crea ficheros.
