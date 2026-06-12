# V730 — Architecture Route Health Visual QA Foundation

## Resumen ejecutivo

V730 añade una capa de control arquitectónico sin mover rutas ni romper funcionalidad. El objetivo es preparar el proyecto para una futura migración gradual desde `app.py` hacia blueprints, pero sin tocar de forma agresiva lo que ya funciona.

## Versión

`V730_ARCHITECTURE_ROUTE_HEALTH_VISUAL_QA_FOUNDATION`

## Cambios principales

- Nuevo motor: `engines/route_health_engine.py`.
- Nueva vista admin: `/admin/route-health`.
- Nueva API admin segura: `/api/admin/route-health`.
- Nuevo script estático: `tools/check_v730_route_health.py`.
- Nuevo informe: `ROUTE_HEALTH_AUDIT_V730.md`.
- Nueva hoja de ruta: `V730_ARCHITECTURE_ROADMAP.md`.
- Enlace a mapa de rutas desde `/admin/system`.
- CSS compacto para la vista de arquitectura.

## Qué aporta

La app ya tenía mucha potencia, pero `app.py` sigue siendo grande. En vez de partirlo todo y arriesgar Render/Telegram/Cron, V730 crea una herramienta para ver:

- total de rutas
- rutas admin
- APIs
- Cron
- rutas cliente
- templates usados
- templates faltantes
- posibles avisos de protección
- blueprint recomendado para cada grupo

## Qué no se ha tocado

- No se movieron rutas.
- No se tocó Render.
- No se tocaron secrets.
- No se tocó `DB_PATH=/data/database.db`.
- No se tocó Telegram automático.
- No se tocó Cron.
- No se tocó Data Memory.
- No se tocó Madrid Time.
- No se rehizo visual cliente V728.
- No se cambió seguridad V729.

## Validación ejecutada en sandbox

- `python -m py_compile app.py engines/route_health_engine.py tools/check_v730_route_health.py`: OK
- `python -m compileall -q app.py engines tools templates`: OK
- `python tools/check_v730_route_health.py`: OK
- `python tools/check_madrid_times.py`: OK
- `python tools/check_v728_client_experience.py`: OK
- `python tools/build_clean_release.py`: OK
- `python tools/audit_release_zip.py`: OK

## Limitación de entorno

El sandbox no tiene Flask instalado, por eso no se completaron `tools/smoke_check.py`, `tools/validate_release.py` ni `pytest -q` aquí. Quedan preparados para local/Render con dependencias instaladas.

## Resultado esperado en Render

- `/api/runtime-version` debe mostrar `V730_ARCHITECTURE_ROUTE_HEALTH_VISUAL_QA_FOUNDATION`.
- `/admin/route-health` debe abrir como admin.
- `/api/admin/route-health` debe devolver JSON solo con sesión admin.
- Usuario no admin debe recibir redirect o 403.

## Veredicto

V730 es una mejora de arquitectura controlada: prepara el siguiente gran paso sin romper lo que funciona.
