# V607 — Error Handling & Observability Center

Actualización limpia para aplicar encima de la carpeta actual de NeMeSiS SHARK PRO.

## Añadido

- Centro admin `/admin/observability`.
- Endpoint `/api/observability/summary`.
- Endpoint `/api/v607/observability-check`.
- Motor `engines/observability_engine.py`.
- Tabla SQLite `observability_events`.
- Tabla SQLite `observability_route_checks`.
- Página controlada para errores 404/500.
- Registro seguro de errores sin exponer claves ni secretos.
- Resumen de salud: DB, errores 24h, cola Telegram, tamaño DB, latencia.

## Archivos incluidos

- `app.py`
- `VERSION.txt`
- `engines/observability_engine.py`
- `templates/admin_observability.html`
- `templates/error_controlled.html`
- `V607_OBSERVABILITY_REPORT.md`
- `INSTALAR_V607.txt`

## Validación

- `python -m compileall app.py engines` OK.
- Sin `.git`.
- Sin `__pycache__`.
- Sin base de datos local.
- Sin logs.

## Nota

Esta actualización no modifica SHARK, Telegram, Auto Picks, membresías ni proveedores de datos. Solo añade control profesional de errores y observabilidad.
