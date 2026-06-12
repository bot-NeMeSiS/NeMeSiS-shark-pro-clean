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

Endpoint:

- `GET /api/automation/data-backup/run?secret=VALOR_REAL`

Si `DATA_BACKUP_ENABLED` no está activo, responde 200 en modo `DISABLED`.

## Restauración

La restauración real debe hacerse con control operativo en Render. V743 deja validación, hash y manifiestos para escoger una copia segura.
