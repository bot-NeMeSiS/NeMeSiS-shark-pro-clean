# V862 Sentinel Cron Runbook

## Endpoint

`/api/automation/shark-sentinel/run`

## Seguridad

Requiere `AUTOMATION_SECRET`. Sin secret debe devolver 403.

## Parámetros

- `dry_run=1`
- `mode=static`
- `mode=diagnostic`

## Comportamiento

Ejecuta inspección estática con Flask test client. No modifica código, no despliega, no envía Telegram real, no toca pagos, no borra datos y no llama APIs caras.
