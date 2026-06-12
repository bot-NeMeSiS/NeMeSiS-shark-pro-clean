# V744 Production Routes QA

## Rutas de control

- `/api/runtime-version`
- `/api/health`
- `/api/startup-check`
- `/api/automation/telegram/tick`
- `/api/automation/daily/run`
- `/api/automation/data-backup/run`

## Criterio

Las rutas de cron deben ser independientes de sesión admin y depender únicamente de `AUTOMATION_SECRET`.

## Resultado esperado

- Sin secret: 403.
- Con secret válido: 200.
- Sin picks o sin backup activo: respuesta controlada, no error 500.
