# V615 ROOT CAUSE TRACE AUDIT

## Cambios realizados

- Se amplió la observabilidad para registrar errores completos en SQLite mediante la nueva tabla `observability_errors`.
- Cada excepción controlada ahora genera un `error_id` con formato `ERR-YYYYMMDD-HHMMSS-XXXX`.
- El handler global guarda:
  - `timestamp`
  - `request.path`
  - `request.method`
  - `endpoint`
  - `user_id`
  - `email`
  - `membership`
  - `exception_type`
  - `exception_message`
  - `traceback_full`
  - `user_agent`
  - `ip`
  - `referrer`
  - `request_id`
  - `app_version`
- Se añadió la vista admin `/admin/observability/errors`.
- Se añadió la API `/api/observability/errors`.
- La pantalla `error_controlled.html` muestra `error_id` y, si la sesión es admin, un enlace directo al detalle del error.
- Se blindaron plantillas críticas para que no revienten si llega un partido incompleto desde proveedores o warehouse:
  - `templates/home.html`
  - `templates/calendar.html`
  - `templates/live.html`
  - `templates/picks.html`
- Se renovaron las plantillas de observabilidad:
  - `templates/admin_observability.html`
  - `templates/admin_observability_errors.html`
  - `templates/error_controlled.html`

## Problemas encontrados

### 1. Causa estructural del ocultamiento

El handler controlado existente sí atrapaba la excepción, pero no guardaba `traceback` ni contexto suficiente para identificar la causa real. Por eso Render enseñaba "Incidencia controlada" sin decir qué ruta, función o línea fallaban.

### 2. Causa raíz técnica más probable en navegación normal

Se detectó un patrón de riesgo real en plantillas críticas: varias vistas asumían que cada partido traía siempre estas estructuras completas:

- `m.live_depth.*`
- `m.home_identity.*`
- `m.away_identity.*`

Eso puede romper el render con datos reales incompletos y derivar en la pantalla controlada. Los puntos más sensibles estaban en:

- `templates/home.html`: acceso a `m.live_depth.label`
- `templates/calendar.html`: acceso directo a `m.home_identity.crest_url` y `m.away_identity.crest_url`
- `templates/live.html`: múltiples accesos directos a `m.live_depth.*`, `m.home_identity.*` y `m.away_identity.*`
- `templates/picks.html`: accesos directos a `m.live_depth.*`, `m.home_identity.*` y `m.away_identity.*`

Se corrigió ese patrón con fallbacks defensivos.

### 3. Limitación honesta de esta auditoría

No fue posible reproducir la excepción HTTP real con Flask test client en esta sandbox porque el runtime local disponible no tiene `flask` instalado. Por tanto:

- no se pudo capturar aquí un `traceback` vivo de la ruta que hoy falla en Render
- sí se dejó instrumentado el sistema para que la próxima incidencia quede registrada con `error_id`, `traceback_full`, ruta y contexto exactos

## Validaciones ejecutadas

- `C:\\Users\\aloha\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe -m compileall app.py engines database_manager.py`
  - Resultado: OK
- Comprobación de disponibilidad de Flask:
  - Resultado: `ModuleNotFoundError: No module named 'flask'`
- Verificación estructural de nuevas piezas:
  - `app.py` registra `/admin/observability/errors` y `/api/observability/errors`
  - `engines/observability_engine.py` crea y consulta `observability_errors`
  - `error_controlled.html` muestra `error_id`

## Rutas probadas

### Probadas estructuralmente en código

- `/`
- `/login`
- `/admin-login`
- `/registro`
- `/cliente-login`
- `/picks`
- `/live`
- `/calendar`
- `/favoritos`
- `/admin/data-center`
- `/admin/observability`
- `/admin/observability/errors`
- `/api/health`
- `/api/runtime-version`
- `/api/startup-check`
- `/api/observability/summary`
- `/api/observability/errors`

### Smoke HTTP real

No ejecutado en esta sandbox por ausencia de Flask.

## Archivos modificados

- `app.py`
- `engines/observability_engine.py`
- `templates/admin_observability.html`
- `templates/admin_observability_errors.html`
- `templates/error_controlled.html`
- `templates/home.html`
- `templates/calendar.html`
- `templates/live.html`
- `templates/picks.html`

## Resumen de error_id funcionando

La pantalla controlada ahora puede mostrar un identificador como:

- `ERR-20260604-183045-4A1F`

Con sesión admin, ese ID enlaza a:

- `/admin/observability/errors?error_id=ERR-20260604-183045-4A1F`

Y la API permite consultar:

- `/api/observability/errors?error_id=ERR-20260604-183045-4A1F`

## Limitaciones pendientes

- Falta ejecutar smoke HTTP real con Flask o directamente en Render.
- Falta provocar o capturar en Render la incidencia que motivó esta auditoría para confirmar con datos en vivo cuál de las rutas críticas era la que estaba cayendo.
- Sigue siendo recomendable revisar más plantillas fuera del núcleo crítico por posibles restos de mojibake heredado.

## Siguiente comprobación en Render

1. Desplegar este estado.
2. Reproducir la navegación que hoy termina en "Incidencia controlada".
3. Anotar el `error_id` mostrado.
4. Abrir `/admin/observability/errors?error_id=...`.
5. Corregir el traceback exacto que aparezca si aún queda otra causa distinta.
