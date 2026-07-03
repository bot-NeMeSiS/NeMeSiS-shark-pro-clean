# V888 AutoPilot Cron QA

## Endpoint

`/api/automation/sentinel-autopilot/run`

## Contrato

- Sin `AUTOMATION_SECRET`: 403.
- Con secret valido local y `dry_run=1`: 200.
- No envia Telegram real.
- No hace deploy.
- No hace push.
- No toca pagos.
- No borra datos.
- Guarda snapshot/tareas solo en memoria controlada.
