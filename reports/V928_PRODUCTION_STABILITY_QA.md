# V928 Production Stability QA

## Estado local

- VERSION.txt y APP_VERSION: V928 y coincidentes.
- Runtime local: `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.
- CSS: cache busting V928 activo.
- Service worker: cache `NEMESIS_CACHE_V928`, sin cache-first para HTML ni CSS.
- Home, cliente, deportes y admin: smokes seguros con DB temporal.
- Jinja, imports, enlaces, Sentinel y checks V928: correctos.
- Browser QA: 156 capturas, cero errores y cero overflow.

## Protecciones preservadas

DB_PATH, Madrid Time, login/sesiones, membresias, Stripe, Telegram dedupe/no-filler, SHARK safe mode, API guards, PWA/404, separacion cliente/admin y hotfixes V923-V927.

## Produccion

V928 no se declara en produccion. La consulta externa desde esta sesion no estuvo disponible y no se realizo push ni deploy. Render debe confirmar explicitamente la version V928, la alineacion de archivos y el cache busting antes de cerrar el despliegue.
