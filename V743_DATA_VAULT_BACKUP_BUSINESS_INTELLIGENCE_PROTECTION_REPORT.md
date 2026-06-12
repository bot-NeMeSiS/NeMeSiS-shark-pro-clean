# V743 Data Vault Backup Business Intelligence Protection

## Estado

Implementado como capa segura sobre la versión estable actual. No cambia `DB_PATH`, no toca secrets y no incluye backups reales dentro del ZIP.

## Cambios aplicados

- Nuevo motor `engines/data_vault_engine.py`.
- Backups SQLite seguros con API nativa de SQLite.
- Formato de backup: `database_YYYYMMDD_HHMMSS.db`.
- Manifiesto JSON con hash SHA-256, versión, tamaño, tablas y resumen de registros.
- Retención por defecto: 30 backups.
- Centro admin: `/admin/data-vault`, `/admin/data-backups`, `/admin/business-intelligence`.
- APIs admin:
  - `/api/admin/data-vault`
  - `/api/admin/data-vault/backups`
  - `/api/admin/data-vault/create-backup`
  - `/api/admin/data-vault/validate-backup`
  - `/api/admin/data-vault/export`
- Cron protegido:
  - `/api/automation/data-backup/run?secret=AUTOMATION_SECRET`

## Seguridad

- Solo admin puede crear, validar o exportar desde panel.
- El cron exige `AUTOMATION_SECRET`.
- `DATA_BACKUP_ENABLED=false` deja el cron en modo seguro sin crear ficheros.
- Los backups y exports quedan fuera del ZIP final.

## Valor comercial

V743 protege usuarios, picks, Telegram, favoritos, warehouse, ROI y datos derivados. La app queda mejor preparada para venta y mantenimiento.

## Pendiente real

- Configurar `DATA_BACKUP_ENABLED=true` en Render cuando se quiera activar backup automático.
- Verificar en producción que `/data/backups` existe en el Persistent Disk.
