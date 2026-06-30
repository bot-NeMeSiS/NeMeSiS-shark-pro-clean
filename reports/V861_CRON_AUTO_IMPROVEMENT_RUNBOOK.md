# V861 Cron Auto-Improvement Runbook

## Endpoint

`/api/automation/auto-improvement/run`

## Seguridad

Requiere `AUTOMATION_SECRET`. Sin secret debe devolver 403.

## Modos

- `dry_run=1`
- `mode=diagnostic`
- `mode=safe`

## Comportamiento

Por defecto ejecuta diagnóstico y devuelve JSON seguro. No modifica código, no despliega, no borra datos, no envía Telegram real y no llama APIs caras.

## Uso recomendado

Ejecutar desde Render Cron solo como diagnóstico protegido. Las acciones sensibles deben aprobarse en admin o ejecutarse manualmente por Codex.
