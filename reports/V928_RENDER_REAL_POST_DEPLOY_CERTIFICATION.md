# V928 Render Real Post-Deploy Certification

## Runtime real

Consulta realizada el 10 de julio de 2026 contra `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.

- Version, APP_VERSION, VERSION.txt y runtime: `V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL`.
- `version_files_match=true`.
- `deployment_alignment_status=aligned_local_files`.
- `static_css_cache_busting=true`.
- Cache del service worker: `NEMESIS_CACHE_V928`.
- `service_worker_no_stale_html_css=true`.
- Sentinel: 0 issues activos y 0 falsos positivos.
- Secret masking: correcto.
- DB_PATH: `/data/database.db`.
- Los nueve flags V928 solicitados estan activos.

## Resultado de certificacion

La identidad de despliegue es correcta, pero la build actualmente servida no se declara estable todavia. Browser QA encontro un timeout en `/live`, 23 respuestas transitorias 502 y tiempos de 9 a 23 segundos en varias rutas deportivas. Las capturas tambien demostraron tres errores de presentacion: payload de forma impreso en el detalle, cuota media visible sin picks completos y cadencia `/mes` duplicada.

Los fallos reproducibles quedaron corregidos localmente dentro de V928, sin crear V929:

- render deportivo cache/DB-only; proveedores solo por job o `refresh=1` explicito;
- forma/historico resumidos sin volcar payload interno;
- cuota media solo desde picks completos con cuota valida;
- cadencia de membresia sin duplicacion;
- home coherente cuando existen partidos hoy pero ninguno es proximo.

Hace falta redesplegar el V928 corregido y repetir el chequeo remoto. No se realizo push ni deploy desde esta certificacion.

Pixel-perfect: no declarado.
