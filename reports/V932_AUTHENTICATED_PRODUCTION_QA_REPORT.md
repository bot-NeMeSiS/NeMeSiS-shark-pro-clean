# V932 Authenticated Production QA Report

## Identidad

- Version: `V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL`
- Base preservada: `V931_PRODUCTION_CLIENT_ROUTES_AND_HOME_DATA_CONSISTENCY_HOTFIX_FINAL`
- `VERSION.txt`, `APP_VERSION` y runtime local: alineados.
- CSS cache busting: activo.
- Service worker: `NEMESIS_CACHE_V932`, sin cache persistente de HTML/CSS antiguo.

## Resultado

V932 protege las vistas autenticadas frente a esquema SQLite antiguo, DB vacia y bloqueos transitorios. Las rutas cliente y admin solicitadas cargaron con sesiones mock aisladas sin usuarios reales, pagos ni envios Telegram. El login y logout mantienen destinos internos y el login admin ya no acepta un `next` externo.

La certificacion autenticada sobre Render no se ejecuto: esta sesion no dispone de una cuenta de prueba real autorizada ni de una sesion autenticada reutilizable. Playwright y Chromium estan disponibles, pero no se ha creado ningun bypass de acceso. Capturas autenticadas de produccion: `0`.

## Cambios aplicados

- Preflight SQLite de solo lectura para rutas autenticadas.
- Fallback coherente y rapido cuando la DB esta bloqueada.
- Contextos seguros para cliente, favoritos y command centers admin.
- Redireccion admin interna y ruta `/admin/logout` separada.
- Diagnostico deportivo admin basado solo en DB/cache.
- Estado cliente comprensible cuando no hay agenda completa.
- Sentinel autenticado deduplicado sin usuario, cookie ni secreto.

## Validacion

- Cliente mock: 10/10 rutas `200`.
- Admin mock: 11/11 rutas `200`.
- API admin sin sesion: `403`.
- SQLite moderno, legacy, vacio y bloqueado: PASS.
- Lectura bloqueada: respuesta segura en aproximadamente 1.625 s por ruta de la matriz.
- Datos deportivos: filtro de campos obligatorios, picks completos y cero llamadas externas en render.
- Jinja: 177 templates parseados.
- Sentinel: 10.0, 39 rutas, 0 incidencias.
- Navegacion: 647 rutas, 932 enlaces, 0 roturas y 0 bucles.
- ZIP/deploy root: PASS, `forbidden_count=0`, `missing_required_root=[]`.

## Produccion

El estado de entrada confirmado es V931 alineada. V932 no se declara en produccion hasta que Render devuelva exactamente la version V932 con `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.
