# V639_RENDER_STARTUP_BLACKSCREEN_REPAIR

## Objetivo
Reparar el fallo de arranque/pantalla blanca o negra en Render y dejar una build limpia lista para GitHub/Render.

## Causa técnica detectada
- La versión subida contenía `rows()` llamando a `seed_core()` en cada consulta. Eso podía reactivar inicialización pesada durante cualquier ruta o render y provocar lentitud, worker restarts o pantalla negra/blanca.
- `/` cargaba `dashboard_data()` completa, que arrastra muchas consultas y módulos secundarios. Para una home pública esto era demasiado pesado.
- Faltaba `/api/startup-check`, citado por versiones/informes anteriores y útil para diagnóstico.
- Había riesgo de errores de plantilla por atributos anidados ausentes (`m.live_depth.label`, `m.home_identity.crest_url`, etc.).
- El ZIP contenía basura de trabajo: `.git`, `.venv`, `__pycache__`, ZIPs internos y carpeta duplicada `v636work`.

## Correcciones aplicadas
- `rows()` ya no ejecuta `seed_core()` automáticamente.
- Añadido `before_request` seguro: inicializa DB solo para rutas reales, no para `/api/health`, `/api/runtime-version`, `/api/startup-check`, `/service-worker.js`, estáticos ni `HEAD`.
- Añadido `after_request` con cabecera de versión y cache-control seguro.
- Añadido `light_home_data()` para que `/` no dispare `dashboard_data()` pesada.
- `/` responde ultraligero en `HEAD` y usa payload ligero en `GET`.
- Añadido `/api/startup-check`.
- Configurado Jinja con `ChainableUndefined` para evitar que campos faltantes rompan toda una pantalla.
- Blindadas plantillas con fallbacks en accesos a `live_depth`, `home_identity` y `away_identity`.
- Actualizada versión a `V639_RENDER_STARTUP_BLACKSCREEN_REPAIR`.
- Generado ZIP limpio sin `.git`, `.venv`, `__pycache__`, DB local, logs, ZIPs internos ni carpetas duplicadas de trabajo.

## Validación ejecutada
- `python -m compileall app.py engines database_manager.py services`: OK.
- Import de app Flask: OK.
- Rutas públicas probadas con Flask test client:
  - `/api/health`: 200
  - `/api/startup-check`: 200
  - `/api/runtime-version`: 200
  - `/`: 200
  - `/login`: 200
  - `/admin-login`: 200
  - `/picks`: 200
  - `/live`: 200
  - `/calendar`: 200
  - `/sports-hub`: 200
- Cliente registrado y probado:
  - `/dashboard`: 200
  - `/perfil`: 200
  - `/telegram`: 200
  - `/favorites`: 200
  - `/combis`: 200
- Admin probado:
  - `/admin/dashboard`: 200
  - `/admin/telegram`: 200
  - `/admin/telegram/diagnostics`: 200
  - `/admin/backups`: 200
  - `/admin/automation`: 200

## Pendiente real
Subir a Render y confirmar que desaparecen en logs:
- `SystemExit`
- `Worker exiting` repetitivo
- errores asociados a `seed_core`
- pantalla blanca/negra en primera carga
