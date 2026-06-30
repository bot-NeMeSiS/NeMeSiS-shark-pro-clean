# V863 Continuous Sentinel Real Run QA

## Local

El runner local seguro se ejecuta con Flask test client, modo `dry_run`, sin llamadas externas y sin modificar código.

Resultado esperado validado por check:

- Estado: diagnóstico seguro.
- No deploy.
- No Telegram real.
- No APIs externas.
- No secretos.
- No escritura SQLite durante render.

## Render real sin sesión/secret

- `/api/admin/continuous-sentinel/summary`: 403
- `/api/admin/continuous-sentinel/run`: 403
- `/api/admin/continuous-sentinel/issues`: 403
- `/api/automation/continuous-sentinel/run` sin secret: 403

## Bloqueo

No se ejecutó `/api/automation/continuous-sentinel/run` con secret porque `AUTOMATION_SECRET` real no está disponible en este entorno.
