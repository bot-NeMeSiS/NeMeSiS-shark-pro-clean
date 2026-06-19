# V818 System Health And Backup QA

El endpoint `/api/automation/health-check?secret=AUTOMATION_SECRET` revisa:

- DB accesible.
- Tablas criticas.
- API-Football configurada.
- The Odds API configurada.
- Telegram configurado.
- `AUTOMATION_SECRET`.
- Errores V818 recientes.

El backup diario reutiliza Data Vault si `DATA_BACKUP_ENABLED=true`; si no, registra salto seguro sin borrar datos.
