# Hallazgos V781 de auditoría completa

## Crítico corregido
1. Ruta duplicada `/admin/launch-certification`.
2. Checks heredados incompatibles con la versión actual.
3. Timestamps crudos visibles en admin.
4. Enlace roto en observabilidad admin.

## Crítico a tener en cuenta fuera del ZIP Render Ready
El árbol fuente completo recibido por ZIP contiene `.git`, `.venv`, `release_output` y módulos raíz duplicados. El ZIP Render Ready generado no incluye esos elementos. Si se sube a GitHub manualmente, debe subirse el ZIP limpio generado o limpiar la carpeta antes de subir.

## Producción Render
Para certificar producción siguen siendo obligatorias pruebas reales de:
- `/api/runtime-version`
- `/live?refresh=1`
- `/api/live/diagnostics?refresh=1`
- `/admin/telegram/command-center`
- `/api/automation/telegram/tick` con `AUTOMATION_SECRET`
- sincronización de escudos/highlights si hay keys reales
