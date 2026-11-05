# Data Backup Runbook V743

## Variables

- `DB_PATH=/data/database.db`
- `DATA_BACKUP_ENABLED=true` para activar backup cron.
- `DATA_BACKUP_MAX_FILES=30` opcional.
- `DATA_BACKUP_DIR=/data/backups` opcional.
- `AUTOMATION_SECRET` obligatorio para cron.

## Crear backup manual

Desde admin:

- Abrir `/admin/data-vault`.
- Usar la acción "Crear backup".

API admin:

- `POST /api/admin/data-vault/create-backup`

## Validar backups

- `POST /api/admin/data-vault/validate-backup`

## Cron de backup

El Master Cron usa `POST /api/automation/data-backup/run` con autenticación en la cabecera `X-Automation-Secret` y cuerpo JSON `{}`. Nunca envíes el secreto en la URL, query string, logs, capturas ni documentación.

No invoques manualmente el endpoint de producción para probar, recuperar o certificar un backup: puede crear archivos, cambiar la retención y actualizar el estado de deduplicación. La certificación requiere una ejecución natural del Cron y evidencia del archivo, manifiesto, SHA-256 e integridad. Una respuesta HTTP 200 por sí sola no acredita que se haya creado una copia válida.

Si `DATA_BACKUP_ENABLED` no está activo, el comportamiento depende del estado de configuración comunicado por el endpoint; no interpretes automáticamente cualquier HTTP 200 como backup correcto.

## Restauración

La restauración real debe hacerse con control operativo en Render. V743 deja validación, hash y manifiestos para escoger una copia segura.
