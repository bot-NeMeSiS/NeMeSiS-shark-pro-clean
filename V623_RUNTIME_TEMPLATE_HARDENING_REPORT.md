# V623 Runtime Template Hardening

## Base revisada
Proyecto actual subido por el usuario.

## Hallazgos principales
- El ZIP contiene el proyecto en versión V622_COMMERCIAL_PRODUCT_HARDENING.
- `compileall` pasa correctamente.
- `rows()` y `execute()` siguen sin inicializar la app.
- La migración segura de `users.telegram_chat_id` está presente.
- Persisten referencias de plantilla potencialmente frágiles a `live_depth`, `home_identity` y `away_identity` en vistas como perfil, favoritos, match hub, team detail, combis y live depth.
- El ZIP subido contiene `.git` y `.venv`; no deben ir en el ZIP final Render Ready.

## Correcciones aplicadas
- Blindadas referencias directas a `live_depth` para evitar errores tipo: `'dict object' has no attribute 'live_depth'`.
- Blindadas referencias directas a `home_identity` y `away_identity` para evitar errores si falta escudo/identidad.
- Añadidos fallbacks seguros para `label`, `badge`, `score`, `minute`, `crest_url` e `initials`.
- Actualizada versión a `V623_RUNTIME_TEMPLATE_HARDENING`.

## Validación
- `python -m compileall app.py engines database_manager.py`: OK.
- Búsqueda de mojibake crítico: sin restos en plantillas principales revisadas.
- ZIP limpio generado excluyendo `.git`, `.venv`, `__pycache__`, bases de datos locales, logs y ZIPs internos.

## Pendiente real
- Probar navegación completa en Render:
  - `/`
  - `/login`
  - `/admin-login`
  - `/perfil`
  - `/picks`
  - `/live`
  - `/calendar`
  - `/admin/telegram`
  - `/admin/observability/errors`
- Si vuelve a aparecer una incidencia controlada, usar el `error_id` y revisar el traceback en observabilidad.
