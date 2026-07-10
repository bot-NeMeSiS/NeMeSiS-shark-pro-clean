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

Render confirma V928, archivos alineados, cache busting y service worker V928. La certificacion remota posterior encontro sincronizaciones externas durante render, un timeout, 23 respuestas 502 transitorias y tres regresiones de presentacion. Esos fallos quedaron corregidos localmente; la estabilidad final queda pendiente de redesplegar el V928 corregido y repetir la matriz remota.
