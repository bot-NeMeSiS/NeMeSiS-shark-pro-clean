# V927 CSS, PWA y Home Picks Truth QA

## Alcance

Esta correccion mantiene la version `V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL`. No cambia producto, diseno, pagos, Telegram, secretos ni datos. Corrige la entrega del CSS/PWA y la verdad del contador de picks activos de la home.

## Estado observado en Render antes del redeploy

- Version: `V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL`.
- `version_files_match=true`.
- `deployment_alignment_status=aligned_local_files`.
- `static_css_cache_busting=false`.
- Hash CSS servido: `6e539dfb7e4446b1`.
- La home cargaba `/static/app.css?v=V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL` y mostraba `6` picks.
- El endpoint publico devolvia 10 picks; al aplicar la regla V927 vigente y completa, 0 eran aptos: 10 estaban vencidos o sin fecha vigente, 8 no tenian seleccion real y 8 no tenian cuota valida.

La consulta fue de solo lectura y no mostro ni modifico registros individuales.

## Correcciones

- `templates/base.html` conserva el query de version V927 y anade una marca de version verificable.
- La home renderizada carga exactamente `/static/app.css?v=V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL`.
- El registro del service worker usa la misma version y `updateViaCache: none`.
- `service-worker.js` usa `NEMESIS_CACHE_V927`, elimina caches anteriores al activar y aplica red primero sin cache para HTML y recarga para CSS/JS.
- La respuesta del service worker se sirve con `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`.
- El runtime detecta el cache busting dinamico correctamente y expone la huella CSS y el estado anti-cache antiguo.
- `static/app.css` incluye una huella V927 nueva. Hash local final: `05d3e9d407cf3b26`.

## Gate de picks

Un pick solo cuenta y se muestra como activo si cumple todo lo siguiente:

- estado `published`;
- resultado pendiente/no liquidado;
- partido identificable con local y visitante;
- fecha vigente y ventana de inicio no vencida;
- partido no finalizado;
- mercado real no generico;
- seleccion real;
- cuota decimal real superior a 1;
- fuente no marcada como fake, demo o placeholder.

Los picks vencidos, ganados/perdidos/anulados, incompletos o de relleno quedan bloqueados. Si no queda ninguno, la home muestra `0` y el estado seguro. No se inventan sustitutos.

La DB local se abrio en modo `read_only`: contiene 0 filas de picks y, por tanto, 0 picks activos completos. Los datos de Render pueden cambiar; el contador se recalcula dinamicamente con el mismo gate tras el redeploy.

## Validaciones

- `py_compile`: OK.
- `compileall`: OK.
- Madrid Time: OK.
- Hotfix V923: OK.
- Home V925 sin hero duplicado: OK.
- Checks desktop V927: OK.
- Check CSS/PWA/picks truth V927: OK.
- Flask smoke: sin 500; home, login, registro, calendario, live, picks, soporte, manifest y service worker en 200; APIs protegidas/404 conservadas.
- Sentinel estatico: OK, sin mutaciones ni datos falsos.
- Imports/rutas: 600, sin templates ni static faltantes.
- Enlaces/rutas: 633, `unsafe_smoke_count=0`.
- Secret Guard: 1956 archivos revisados, 0 findings.
- Browser QA/pixel-perfect: sigue pendiente/no permitido.

## Verificacion posterior al redeploy

No basta con que Render siga diciendo V927, porque ya existia una compilacion V927 anterior. Confirmar tambien:

- `static_css_cache_busting=true`;
- `static_css_hash=05d3e9d407cf3b26`;
- `service_worker_cache_name=NEMESIS_CACHE_V927`;
- `service_worker_no_stale_html_css=true`;
- la home no conserva el contador antiguo de 6 si esos registros siguen vencidos/incompletos.
