# V766 Highlights Automation Runbook

## Endpoint Cron protegido
`/api/automation/highlights/sync?secret=AUTOMATION_SECRET`

Parámetros opcionales:
- `force=1`
- `days_back=5`
- `limit=250`

## Variables necesarias
- `AUTOMATION_SECRET`
- `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`

## Uso recomendado
Crear un Cron diario en Render, por ejemplo por la mañana Madrid, que llame este endpoint. También puede ejecutarse manualmente desde admin con `/api/admin/highlights/sync`.

## Seguridad
El endpoint automático exige `AUTOMATION_SECRET`. No expone keys ni descarga vídeos.
