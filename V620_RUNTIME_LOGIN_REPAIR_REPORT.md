# V620_RUNTIME_LOGIN_REPAIR

## Objetivo
Reparar los errores reales detectados al entrar como cliente/admin y validar el runtime con Flask test client usando el proyecto actual como base.

## Causa raíz corregida
1. `init_db()` mantenía una conexión SQLite abierta mientras ejecutaba migraciones de engines que abrían sus propias conexiones. En rutas protegidas como `/picks`, `/live` o `/admin`, esto podía bloquear SQLite durante la primera inicialización runtime.
2. `/admin/data-center` podía terminar en incidencia controlada por claves faltantes en el diccionario `data`, especialmente `data.shark_accuracy` y listas de `data.shark_memory`.
3. Existía una consulta legacy en `api_sync_logs` que pedía `created_at`, pero la tabla usa `started_at`.
4. `startup_after_request()` intentaba iniciar trabajos diferidos aunque `STARTUP_SCHEDULER_ENABLED` estuviera desactivado, añadiendo ruido y trabajo innecesario por ruta.
5. Quedaba texto visible con errores en `templates/global.html`.

## Cambios aplicados
- `init_db()` ahora cierra y confirma la conexión principal antes de ejecutar migraciones externas de engines.
- Se añadieron fallbacks seguros para `shark_accuracy`, `best_ventajas` y `risk_ventajas` en Data Center.
- Consulta de logs corregida: `started_at AS created_at`.
- Scheduler diferido solo intenta arrancar si `scheduler_enabled()` y `scheduler_startup_enabled()` están activos.
- Texto corregido: “mapa mundial”, “fútbol”, “España”, “Andalucía”, “módulo”.
- Versión actualizada a `V620_RUNTIME_LOGIN_REPAIR`.

## Validación ejecutada
- `python3 -m compileall -q app.py engines database_manager.py`: OK.
- Flask test client disponible y ejecutado.

## Rutas comprobadas sin 500
- `/api/health` → 200
- `/api/runtime-version` → 200
- `/api/startup-check` → 200
- `/` → 200
- `/login` → 200
- `/admin-login` → 200
- `/registro` → 200
- `/picks` → 200
- `/live` → 200
- `/calendar` → 200
- `/admin/data-center` sin sesión → 302 a admin-login
- `/admin/observability` sin sesión → 302 a admin-login
- `/admin/observability/errors` sin sesión → 302 a admin-login
- `/api/observability/summary` sin sesión → 403
- `/api/observability/errors` sin sesión → 403

## Flujos comprobados
- Registro cliente → 302 a `/perfil`.
- Login cliente → 302 a `/perfil`.
- `/perfil` autenticado → 200.
- Login admin con `ADMIN_USERNAME/ADMIN_PASSWORD` → 302 a `/admin/import-center`.
- `/admin/data-center` autenticado → 200.
- `/admin/observability` autenticado → 200.
- `/admin/observability/errors` autenticado → 200.
- `/admin/dashboard` autenticado → 200.

## Estado final
Build limpio preparado para Render. No se han tocado funcionalidades SHARK, Telegram, Warehouse ni membresías salvo fallbacks defensivos para evitar 500 en navegación.
