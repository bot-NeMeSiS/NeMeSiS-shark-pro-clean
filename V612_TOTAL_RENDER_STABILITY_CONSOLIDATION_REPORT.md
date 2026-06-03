# V612 — Total Render Stability Consolidation

## Causa raíz exacta

La reparación V611 eliminó la pantalla negra de arranque, pero quedaban fuentes de 500 al entrar o navegar:

- `dashboard_data()` no estaba protegido: cualquier fallo en una subsección secundaria podía tumbar `/perfil`, dashboards, picks o admin.
- `create_user()` seguía llamando a `seed_core()`, lo que hacía pesado el registro y podía disparar inicialización/seed en pleno flujo de usuario.
- `default_profile()` seguía llamando a `seed_core()` y escribiendo perfil por defecto durante lectura de dashboard.
- El formulario de `admin_login.html` construía mal el `action` cuando había `next`: `/admin-loginnext=...` en vez de `/admin-login?next=...`.
- `/admin/observability` redirigía con `url_for("admin_login")`, endpoint inexistente en esta app, lo que podía provocar 500 en usuarios no autenticados.

## Reparaciones aplicadas

- `dashboard_data()` queda protegido con wrapper:
  - `_dashboard_data_full()` mantiene la funcionalidad completa.
  - `dashboard_data()` captura excepciones y devuelve estructura mínima válida.
- `default_profile_minimal()` añadido para fallback sin DB pesada.
- `default_profile()` ya no ejecuta `seed_core()` ni inserta datos durante lectura.
- `create_user()` ya no ejecuta `seed_core()`.
- `admin_login.html` corrige `?next=`.
- `/admin/observability` redirige a `/admin-login?next=/admin/observability`.
- Se mantiene la regla V611:
  - `rows()` no llama a `seed_core()`.
  - `/` no llama a `dashboard_data()`.
  - `/api/health` no toca DB.
  - scheduler no arranca durante import.

## Validación crítica

Ejecutado:

`python -m compileall app.py engines database_manager.py`

Resultado: OK.

Checks estáticos ejecutados:

- `rows_calls_seed_core`: False.
- `home_calls_dashboard_data`: False.
- `health_calls_db`: False.
- `import_level_scheduler`: False.
- `calendar_alias`: True.
- `dashboard_fallback`: True.
- `create_user_calls_seed_core`: False.
- `admin_login_action_fixed`: True.

## Rutas revisadas

- `/`
- `/login`
- `/admin-login`
- `/registro`
- `/picks`
- `/live`
- `/calendar`
- `/admin/data-center`
- `/api/health`
- `/api/startup-check`
- `/api/runtime-version`
- `/admin/observability`
- `/api/observability/summary`

## Test client Flask

No se pudo ejecutar localmente porque el runtime disponible no trae Flask y la instalación con `pip install -r requirements.txt` está bloqueada por red/permisos:

`WinError 10013: Intento de acceso a un socket no permitido`

En Render, `requirements.txt` instala Flask durante el build.

## Variables Render necesarias

Obligatorias:

- `SECRET_KEY`
- `DB_PATH=/data/database.db`

Recomendadas:

- `ADMIN_EMAIL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SCHEDULER_ENABLED`
- `STARTUP_AUTO_SYNC`
- `AUTONOMOUS_CRON_TOKEN`

Opcionales por proveedor:

- `THESPORTSDB_API_KEY`
- `THE_ODDS_API_KEY`
- `API_FOOTBALL_KEY`

## Render Ready

La app queda preparada para:

- importar `app.py` sin ejecutar procesos pesados;
- responder `HEAD /`;
- responder `/api/health`;
- entrar a login/registro sin cargar dashboard completo;
- evitar 500 por módulos secundarios gracias al fallback de `dashboard_data()`;
- mantener funcionalidades actuales sin eliminar motores existentes.

