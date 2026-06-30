# V861 Render Ready Auto-Improvement Notes

## Release

V861 está preparado como capa de diagnóstico seguro para Render, sin nuevas llamadas externas por render.

## Variables

El endpoint cron requiere `AUTOMATION_SECRET`, ya preservado por la arquitectura V818.

## Honestidad operativa

Esta versión no prueba Render real por sí misma. El estado real de Render, Telegram, APIs y pagos debe validarse en el entorno desplegado.

## ZIP

El ZIP final debe construirse con `tools/build_clean_release.py` y auditarse con `tools/audit_release_zip.py`.
