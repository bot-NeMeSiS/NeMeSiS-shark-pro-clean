# V611 — Render Startup Definitive Repair

## Causa raíz exacta

Render hacía `HEAD /` y la ruta `/` llamaba a `dashboard_data()`. Esa cadena acababa en `get_matches() -> rows() -> seed_core() -> _seed_core_unlocked() -> init_db()`.

El problema crítico era que `rows()` llamaba a `seed_core()`. Por tanto, cualquier `SELECT` podía disparar inicialización, schema, seed, limpieza/scheduler y consultas pesadas. En una primera petición de Render, Gunicorn podía matar el worker por timeout antes de servir la home.

También había arranque de scheduler a nivel de import mediante `schedule_auto_sync_if_needed()`, lo que permitía trabajo de fondo antes de que la app estuviera sana.

## Reparación aplicada

- `rows()` ya no llama a `seed_core()`.
- `rows()` solo ejecuta SELECT, cierra conexión y registra `[ROWS]` si falla.
- Añadido `execute()` para SQL de escritura sin inicializar app.
- Añadido patrón idempotente:
  - `init_db_schema()`
  - `seed_core_data()`
  - `initialize_once()`
  - `start_background_jobs()`
- Añadidas banderas:
  - `APP_INITIALIZED`
  - `APP_INIT_ERROR`
  - `APP_INIT_AT`
- `/` usa `light_home_data()` y ya no llama a `dashboard_data()`.
- `HEAD /` queda ligero porque comparte la misma ruta `/`.
- Login, admin-login y registro usan datos ligeros en GET.
- GET público de login/registro/admin-login omite inicialización; POST sí inicializa schema antes de autenticar o registrar.
- `/api/health` es ultraligero y no toca DB, SHARK, warehouse ni scheduler.
- Añadidos:
  - `/api/startup-check`
  - `/api/runtime-version`
- Scheduler diferido:
  - ya no se ejecuta en import.
  - solo intenta arrancar después de una respuesta correcta y con app inicializada.
- Error handler 500 ya no intenta cargar `dashboard_data()`.
- Alias `/calendar` añadido sobre la ruta existente `/calendario`.

## Logs añadidos

- `[STARTUP]`
- `[DB_INIT]`
- `[SEED]`
- `[ROWS]`
- `[HEALTH]`
- `[RENDER]`
- `[SCHEDULER]`

## Validación ejecutada

- `python -m compileall app.py engines database_manager.py`: OK.
- Validación estática crítica:
  - `rows_calls_seed_core`: False.
  - `home_calls_dashboard_data`: False.
  - `health_calls_db`: False.
  - `import_level_scheduler`: False.

## Test client Flask

Intentado instalar dependencias locales con `pip install -r requirements.txt`, pero el entorno bloquea red/sockets:

`WinError 10013: Intento de acceso a un socket no permitido`

Por eso no se pudo ejecutar Flask test client localmente en este PC. En Render sí se instalan `requirements.txt` durante build.

## Resultado esperado en Render

- `gunicorn app:app` puede importar sin arrancar scheduler.
- `HEAD /` no inicializa DB completa.
- `/api/health` responde sin DB ni módulos pesados.
- `/api/runtime-version` muestra la versión real cargada.
- Se elimina la causa directa del worker timeout observada en logs.
