# V862 Render Ready Continuous Sentinel Notes

## Render

El endpoint `/api/automation/continuous-sentinel/run` requiere `AUTOMATION_SECRET`.

## Seguridad

No realiza llamadas externas, no escribe SQLite durante render y no ejecuta acciones peligrosas.

## Release

El ZIP final debe construirse con `tools/build_clean_release.py` y auditarse con `tools/audit_release_zip.py`.
