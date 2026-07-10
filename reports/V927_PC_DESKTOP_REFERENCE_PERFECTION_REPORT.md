# V927 PC Desktop Reference Perfection Report

## Identidad

- Version local: `V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL`.
- Base usada: `V926_DESKTOP_REFERENCE_MODEL_COMMAND_CENTER_AND_SPORTS_VALUE_PASS_FINAL`.
- Produccion comprobada antes del cierre CSS/PWA: una compilacion V927 anterior, alineada y con Sentinel en 0 issues activos, pero con `static_css_cache_busting=false`.
- La entrega V927 definitiva no se considera activa hasta que Render confirme tambien el hash CSS `05d3e9d407cf3b26` y `static_css_cache_busting=true`.

## Resultado

V927 aplica una capa de escritorio exclusiva desde 1024 px. Compacta la zona superior, amplia el lienzo util, ordena KPIs, filtros, tablas, operaciones y siguiente accion. Se han actualizado home, cliente, calendario, live, picks, SHARK, Telegram, perfil, membresias y los command centers admin.

Se mantienen los guards V923-V926, los contextos deportivos sin llamadas externas durante render, la separacion cliente/admin, Madrid Time, PWA/404, DB_PATH, Telegram dry-run/no filler/dedupe y el gate de screenshots.

## Verdad visual

- Referencias locales revisadas: 16 imagenes reales, 1672x941.
- Browser QA final V927: pendiente; el navegador de esta sesion no pudo adjuntar la vista de produccion.
- Pixel-perfect: no declarado.
- Datos inventados: no.
- Cola visual: no se desbloquea sin screenshot valido.

## Cambios de valor

- Home: hero de PC reducido, cinco estados arriba y secciones compactas.
- Cliente: seis KPIs, estado seguro y siguiente accion above-the-fold.
- Deportes: toolbar de fuente/sync/cache, filtros inmediatos y tabla segura de picks.
- Admin: jerarquia KPI -> operaciones -> siguiente accion -> tablas.
- Perfil y planes: comparacion en tres columnas y estado Stripe honesto.

## Cierre CSS/PWA y picks

- Render ya llego a una compilacion V927 anterior, pero esa compilacion aun reportaba `static_css_cache_busting=false`.
- La entrega final V927 usa el hash CSS `05d3e9d407cf3b26`, cache `NEMESIS_CACHE_V927` y politica network-first/no-store para HTML y recarga para CSS/JS.
- El contador de picks de home solo incluye publicados, vigentes y completos. La muestra publica observada de 6 no supero el gate actual; el estado seguro sera 0 mientras no existan picks reales validos.
- QA detallado: `reports/V927_CSS_PWA_AND_HOME_PICKS_TRUTH_QA.md`.

## Despliegue

Subir el contenido interno de `release_output/V927_DEPLOY_ROOT_CONTENTS` a la raiz del repositorio. Tras Render, comprobar version, `version_files_match=true`, `deployment_alignment_status=aligned_local_files`, `static_css_cache_busting=true`, hash CSS `05d3e9d407cf3b26` y los cinco flags V927.
