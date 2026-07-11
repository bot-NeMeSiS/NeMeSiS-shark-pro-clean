# V931 Production Client Routes Hotfix

## Identidad

- Version local: `V931_PRODUCTION_CLIENT_ROUTES_AND_HOME_DATA_CONSISTENCY_HOTFIX_FINAL`
- Base preservada: `V930_CANONICAL_REFERENCE_VISUAL_PARITY_ADMIN_CLIENT_MOBILE_FINAL`
- Navegacion V929: preservada y validada.
- Redisenio V930: preservado y validado.
- Alcance: recuperacion de rutas cliente, compatibilidad con esquemas SQLite antiguos, coherencia de la home y errores 500 seguros.

## Cambios aplicados

- `rows()` cierra siempre su conexion SQLite, incluso cuando falla una consulta.
- Las rutas criticas usan contexto DB/cache tolerante a tablas o columnas ausentes.
- `/calendar`, `/live` y `/picks` ya no dependen de una consulta rigida a `matches.priority` para renderizar.
- `/live` no llama proveedores externos durante el render.
- `/app`, `/profile`, `/memberships`, `/shark`, `/telegram` y `/track-record` tienen fallback seguro ante schema drift.
- `/cliente-login` conserva su render publico y una sesion activa redirige a un `/app` ya protegido.
- La home usa una unica fuente de verdad para su contador y su lista visible.
- Registros deportivos incompletos quedan fuera del resumen valido y se clasifican como `incomplete_matches`.
- HTML 500 usa `templates/500.html`; API 500 devuelve JSON seguro, sin traceback.
- Las incidencias de rutas criticas se deduplican por version, ruta y tipo de excepcion.

## Resultado

- Matriz V931: 81 comprobaciones de ruta, 0 fallos.
- Perfiles: DB normal, DB vacia, esquema antiguo y DB bloqueada.
- Jinja: 177 templates parseados.
- Sentinel: 10.0, 39 rutas, 0 incidencias activas.
- Imports/rutas: 612 rutas verificadas, 0 templates o static ausentes.
- Navegacion: 646 rutas y 931 enlaces, 0 enlaces rotos, 0 bucles.
- Acciones peligrosas ejecutadas: no.
- Telegram real, pagos reales y DB real: no tocados.

## Archivos principales

- `app.py`
- `templates/home.html`
- `templates/500.html`
- `tools/check_v931_production_client_routes_hotfix.py`
- `tools/check_v929_navigation_integrity.py`
- `tools/v930_check_support.py`
- `tools/build_clean_release.py`
- `VERSION.txt`
- `APP_VERSION`

V931 no se considera en produccion hasta que Render publique esta version exacta y confirme `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.
