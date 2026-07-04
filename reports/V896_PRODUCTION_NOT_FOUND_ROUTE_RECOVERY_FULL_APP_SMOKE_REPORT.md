# V896 Production Not Found Route Recovery Full App Smoke

## Objetivo

Eliminar la experiencia seca de `Not Found` en NeMeSiS SHARK PRO y convertir cualquier ruta perdida en una recuperación segura, premium y medible.

## Estado de producción revisado

Endpoint consultado:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado en esta sesión:

- Producción responde una versión antigua: `V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL`.
- `app_py_path`: `/opt/render/project/src/app.py`.
- `db_path`: `/data/database.db`.

Esto confirma que el problema puede venir de mezcla de deploy/caché/rutas antiguas/PWA, aunque V896 corrige la experiencia de 404 en el código local.

## Causa probable

El usuario puede ver `Not Found` por una de estas causas:

- Acceso directo antiguo o ruta vieja.
- PWA instalada con `start_url` viejo.
- Caché móvil conservando navegación anterior.
- Link interno antiguo.
- Ruta admin o cliente renombrada.
- Render sirviendo una versión distinta de la local.
- Ausencia de handler 404 premium en versiones anteriores.

## Cambios V896

- Nueva página premium: `templates/404.html`.
- Nuevo handler Flask `@app.errorhandler(404)`.
- Respuesta JSON controlada para `/api/*` no existentes.
- Memoria segura de 404: `data/runtime/not_found_events.json`.
- Integración con Sentinel Issues para registrar `Ruta devuelve Not Found`.
- Nuevas APIs admin protegidas:
  - `/api/admin/route-map`
  - `/api/admin/route-smoke`
  - `/api/admin/not-found-events`
- Manifest PWA seguro en `/manifest.json`.
- Service worker V896 con `NEMESIS_CACHE_V896` y limpieza de caches antiguas.
- `base.html` incluye manifest y cache marker V896.
- Runtime añade `has_v896_not_found_route_recovery=true`.

## Aliases creados

Cliente:

- `/dashboard` -> `/app`
- `/client` -> `/app`
- `/cliente` -> `/app`
- `/client-dashboard` -> `/app`
- `/home` -> `/`
- `/inicio-cliente` -> `/app`
- `/mi-cuenta` -> `/profile`
- `/perfil` -> `/profile`
- `/soporte` -> `/support`
- `/ayuda` -> `/support`
- `/partidos-hoy` -> `/calendar`
- `/calendario` -> `/calendar`
- `/directos` -> `/live`
- `/en-vivo` -> `/live`
- `/recomendaciones` -> `/picks`
- `/pick` -> `/picks`
- `/apuestas` -> `/picks`

Admin:

- `/admin-panel` -> `/admin/dashboard`
- `/admin/home` -> `/admin/dashboard`
- `/admin/control` -> `/admin/dashboard`
- `/admin/sentinel` -> `/admin/autonomous-company-sentinel`
- `/admin/qa` -> `/admin/autonomous-company-sentinel`
- `/admin/prompts` -> `/admin/sentinel-codex-outbox`

Rutas ya existentes no se duplican:

- `/admin/autopilot`
- `/admin/issues`

## PWA y Service Worker

Manifest:

- `name`: NeMeSiS SHARK PRO
- `short_name`: NeMeSiS
- `start_url`: `/`
- `scope`: `/`
- `display`: `standalone`

Service worker:

- Cache actual: `NEMESIS_CACHE_V896`.
- Limpia caches antiguas en `activate`.
- Para navegación offline o fallo de red, recupera `/`.

## Cómo limpiar caché PWA si el usuario sigue viendo Not Found

En móvil:

1. Cerrar la app instalada.
2. Abrir el navegador.
3. Ir a configuración del sitio de `bot-apuestas-crgf.onrender.com`.
4. Borrar datos/caché del sitio.
5. Si está instalada como PWA, eliminarla y volver a instalarla tras desplegar V896.
6. Abrir `/api/runtime-version` y confirmar V896.

En escritorio:

1. Abrir DevTools.
2. Application.
3. Service Workers.
4. Unregister.
5. Storage -> Clear site data.
6. Recargar.

## Eventos 404

Se guardan en:

`data/runtime/not_found_events.json`

Se pueden consultar desde admin:

`/api/admin/not-found-events`

Sin sesión admin devuelve 403.

## Integración Sentinel

Cada 404 genera o actualiza una incidencia segura:

- Área: `navigation`
- Título: `Ruta devuelve Not Found`
- Severidad: `high` para rutas principales/admin o repetidas
- Severidad: `medium` para rutas secundarias

No se guarda secreto, token ni dato sensible.

## Validación esperada

Smoke local:

- `/` = 200
- `/app` = 302 o 200
- `/cliente-login` = 200
- `/registro` = 200
- `/calendar` = 200
- `/live` = 200
- `/picks` = 200
- `/support` = 200
- `/admin-login` = 200
- `/admin/dashboard` sin sesión = redirect/403 controlado
- `/admin/autonomous-company-sentinel` sin sesión = redirect/403 controlado
- `/api/runtime-version` = 200
- `/ruta-inventada` = 404 premium
- `/api/ruta-inventada` = JSON 404 controlado
- `/dashboard` = redirect `/app`
- `/admin-panel` = redirect `/admin/dashboard`
- `/directos` = redirect `/live`

## Limitaciones honestas

- No se hizo deploy automático.
- No se hizo push.
- No se tocaron secretos.
- No se borró DB.
- No se enviaron Telegram reales.
- No se probaron pagos reales.
- Render debe desplegar V896 para que producción deje de mostrar versiones antiguas.

## Post-deploy

Después de subir V896 a GitHub `main` y hacer `Clear build cache & deploy` en Render:

1. Abrir `/api/runtime-version`.
2. Confirmar `app_version = V896_PRODUCTION_NOT_FOUND_ROUTE_RECOVERY_FULL_APP_SMOKE_FINAL`.
3. Probar:
   - `/`
   - `/app`
   - `/cliente-login`
   - `/admin-login`
   - `/dashboard`
   - `/admin-panel`
   - `/ruta-inventada`
4. Si aparece un `Not Found` seco, documentar la URL exacta como blocker.
