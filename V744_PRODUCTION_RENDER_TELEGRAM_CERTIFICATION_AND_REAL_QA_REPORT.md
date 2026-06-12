# V744 Production Render Telegram Certification and Real QA

## Estado

V744 refuerza la certificación de producción sin cambiar Telegram, SHARK ni Picks.

## Certificado

- `/api/runtime-version` muestra versión, DB, cron, Telegram y backup.
- `/api/automation/telegram/tick` sigue protegido con secret.
- `/api/automation/daily/run` sigue protegido con secret.
- `/api/automation/data-backup/run` añadido y protegido con secret.
- El cron sin secret devuelve 403.
- El cron con secret devuelve 200.
- El backup cron queda desactivado por defecto si `DATA_BACKUP_ENABLED` no está activo.

## No se toca

- Envío manual Telegram.
- Cola Telegram.
- Dedupe.
- Scheduler existente.
- Daily automation.
- DB_PATH.

## Pendiente en Render

- Confirmar variables reales.
- Crear Cron Jobs en Render apuntando a los endpoints certificados.
- Activar `DATA_BACKUP_ENABLED=true` solo cuando se quiera backup automático real.
