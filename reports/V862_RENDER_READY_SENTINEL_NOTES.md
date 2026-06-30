# V862 Render Ready Sentinel Notes

## Render

V862 no añade llamadas externas nuevas durante render. El endpoint cron requiere `AUTOMATION_SECRET`.

## Browser QA

No se declara navegador real ni pixel-perfect. El modo por defecto es `MODE_STATIC_FLASK_CLIENT`.

## Release

El ZIP final debe construirse con `tools/build_clean_release.py` y auditarse con `tools/audit_release_zip.py`.
