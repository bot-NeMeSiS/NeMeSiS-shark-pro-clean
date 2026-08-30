# Architecture Consolidation Report

Estado del documento: `PASS_LOCAL`; promoción a producción pendiente de reconfirmación explícita del commit de purga.

## Decisión ejecutiva

La causa estructural principal no era una ruta rota: era una cascada histórica donde shell, contenido y navegación competían en el mismo contexto de apilado, acompañada por listeners duplicados, versiones de asset divergentes y miles de evidencias regenerables dentro de Git.

La consolidación aplicada reduce el índice del repositorio, establece una autoridad visual explícita, mantiene las capas de compatibilidad que siguen activas y añade regresiones permanentes. No se ha modificado Sports Core, SHARK lógico, auth, membresías, Telegram, Stripe, DB, Growth ni Continuous Evolution.

## PRE_CONSOLIDATION_BASELINE

| Evidencia | Resultado |
|---|---|
| Local/origin/Render SHA | `fc743709d6588148285f33a3c783e220bfa86483` alineados |
| Git inicial | limpio, `main`, ahead/behind `0/0` |
| Archivos Git | 10.749 |
| Python Git | 1.544 |
| Templates | 199 |
| CSS Git / CSS activo | 10 / 8 |
| JS Git / JS activo | 7 / 5 |
| Engines | 157 físicos |
| Workers | 34 archivos, 33 módulos excluyendo `__init__` |
| Tests pytest | 48 archivos |
| Static assets | 16 |
| Reports Git | 5.236 |
| `app.py` | 29.970 líneas |
| Pytest completo | 326 PASS |
| Product QA | 57 capturas, 18 clicks topbar, 8/8 Golden Journeys, 0 errores JS/página |
| Routes/links | PASS; 807 reglas runtime con `static` |
| Sports P0 | PASS local |
| Performance P0 | budgets de comportamiento PASS; verificadores de versión histórica clasificados obsoletos |
| Privacy/Secret/Rights/Jinja/Smoke | PASS |

## Inventario y clasificación

| Clase | Contenido actual | Decisión |
|---|---|---|
| `CANONICAL` | `app.py`, engines de dominio, templates base, tokens V933, `v933-product.css`, contratos y tests | conservar |
| `ACTIVE_REQUIRED` | templates 199, CSS/JS cargados, aliases públicos, 316 evidencias runtime consumidas | conservar hasta migración probada |
| `LEGACY_ACTIVE` | `app.css`, V928, V930, V936 y V937 | compatibilidad controlada; no retirar sin pantalla por pantalla |
| `LEGACY_SHADOWING` | contexto de apilado topbar, fondo móvil duplicado, listeners nav duplicados | corregido localmente |
| `DUPLICATE` | 4 handlers nav y 2 árboles nav muertos | retirados |
| `DEAD_CODE` | bloque `{% if false %}`, bottom nav antigua, `shark-logo.svg` sin referencias | retirados |
| `GENERATED` | Browser QA, screenshots, vídeos, entornos virtuales | fuera del índice; copias locales preservadas |
| `RUNTIME` | `data/runtime` | deuda controlada, no purgada sin prueba de release |
| `QA_ARTIFACT` | 6.674 entradas desversionadas | ignoradas por Git |
| `REPORT_ONLY` | 2.030 informes raíz | históricos; no se borran porque existen consumidores nominales |
| `UNKNOWN` | cualquier fichero sin trazado completo | no borrar |

El inventario canónico detecta 1.801 archivos fuente (74,7 MB) y 8.634 evidencias físicas (3,206 GB). La reducción de Git no borra esas evidencias del equipo.

## Dependencias y ownership

- Exact source duplicates: 0 grupos.
- Templates: 199; 179 extienden `base.html`; 20 son parciales/macros; 95 relaciones include/import; 0 duplicados exactos.
- Runtime routes: 806 sin `static`, 564 endpoints, 136 endpoints con más de una regla compatible.
- Métodos: GET 743, POST 164, DELETE 2.
- Dominio: Admin 231, Admin API 184, otras API 118, Sports API 28, Automation 19, Sports Client 35, Auth/Account 7, Public/Other 184.
- La matriz de enlaces actual inspecciona los 198 templates aplicables y no detecta href vacío, `javascript:void(0)` ni formularios sin action.

Los aliases que comparten endpoint se clasifican `SAFE_ALIAS` mientras mantengan mismo handler, auth y respuesta. `V896_ROUTE_ALIASES` conserva compatibilidad explícita; las rutas únicas son `CANONICAL`. No se eliminó ninguna URL pública.

## App.py

`app.py` sigue siendo el mayor riesgo de acoplamiento: 29.970 líneas, 1.393 funciones y 170 llamadas de render. No se hizo extracción Big Bang. El orden seguro está en [APP_PY_DECOMPOSITION_PLAN.md](APP_PY_DECOMPOSITION_PLAN.md).

## CSS cascade map

| Orden | Hoja | Papel |
|---:|---|---|
| 1 | `app.css` | legado activo y compatibilidad amplia |
| 2 | `v928-canonical.css` | shell/componentes compatibles |
| 3 | `v930-canonical.css` | UI compatible |
| 4 | `v933_design_tokens.css` | tokens canónicos |
| 5 | `v936-commercial.css` | Growth/Revenue activo |
| 6 | `v937-product-client.css` | cliente específico activo |
| 7 | `v937-sports-lifecycle.css` | estados deportivos activos |
| 8 | `v933-product.css` | autoridad visual global, cargada última |

Hay 9.716 selectores únicos, 6.027 repeticiones y 223 selectores cruzados. Esto es deuda real, pero no demuestra por sí solo que una regla sea eliminable. La autoridad para fondo, shark, shell, topbar, cards y responsive queda en tokens V933 + `v933-product.css`; las capas anteriores se consideran `LEGACY_ACTIVE`, no canónicas.

### Capas

`BACKGROUND < ATMOSPHERE < CONTENT < STICKY < NAVIGATION < DROPDOWN < MODAL < TOAST`. Decoración y wrapper de chrome usan `pointer-events:none`; enlaces, botones y controles reactivan `pointer-events:auto`.

## Topbar

Root cause demostrado: un selector global asignaba `position:relative; z-index:2` tanto al wrapper del chrome como al contenido posterior. El contenido creaba un hermano apilado encima; el alto z-index interno de la topbar no podía escapar de su stacking context. Además coexistían cuatro rutinas que recalculaban navegación activa.

Corrección: wrapper chrome sin stacking context propio, contenido en nivel canónico, controles interactivos explícitos y una única delegación `pointerdown` sobre `[data-nav-zone]`. El árbol de links público se genera desde una sola lista Jinja. Resultado local: 8/8 clicks reales desktop y tablet, destino y HTTP correctos.

## Shark y background

- `BRAND_SHARK`: `static/img/nemesis-shark-official.svg`, geometría compacta 188x96 y cache key `official-brand-8`.
- `ATMOSPHERIC_SHARK`: `static/img/nemesis-shark-atmosphere.svg`, cache key única `official-atmosphere-7`.
- `shark-logo.svg`: 0 referencias activas, 0 requests en Browser QA, retirado.
- Las clases decorativas V810/V815/V825 se neutralizan en la autoridad V933.
- Se eliminó el override móvil que deformaba el fondo global y se redujeron crop/opacidad/escala por superficie.

Estado: `FOUNDER_REVIEW_READY`. Carga correcta no equivale a aprobación visual; no se declara `RESOLVED` antes de comparar producción con las 16 referencias y recibir aprobación del fundador.

## JavaScript y PWA

Hay 5 JS estáticos y 0 funciones nombradas duplicadas entre archivos. `base.html` carga iconos, realtime, cliente y sports lifecycle; calendario carga su módulo contextual. Se retiraron cuatro handlers nav redundantes.

El service worker V940 usa HTML navigation `network-first/no-store`, CSS/JS `cache:reload`, borra caches anteriores en `activate`, reclama clientes y se sirve con `Cache-Control: no-store`. Las claves visuales quedaron unificadas; no se pasan valores distintos para el mismo SVG.

## Workers

De 33 módulos operativos, 17 son adaptadores finos sobre dos ejecutores comunes: 10 V935 y 7 de referencia V928. No son 17 motores independientes. Ownership conceptual:

- Quality: QA Director, Digital User, Visual Inspector, Regression Manager, Production Sentinel.
- Sports: Sports Data, Sports Truth, Sports Knowledge, SHARK.
- Operations: Reliability, Security, Rights.
- Business: Growth, Revenue, Marketing, CRM/Customer Success.
- Executive: Executive Board, Founder Brief, Prepared for Codex.

No se borraron wrappers porque herramientas, informes y orquestadores todavía importan sus nombres. La siguiente consolidación debe mantener entrypoints compatibles y mover capacidades menores a responsables comunes.

## Issue ledger

La memoria contiene 871 IDs únicos: 864 `RESOLVED_BY_RESCAN`, 2 `STALE_NEEDS_REVALIDATION` y 5 `OPEN`. No hay IDs duplicados. Los siete activos eran ruido demostrable: probes 404 intencionados o estados vacíos deportivos premium que el diccionario no reconocía.

Se corrigió el intake: los probes llevan `X-NEMESIS-QA-PROBE`, no crean issues reales, y el worker reconoce los textos actuales de Partidos/Calendar/Live. La historia no se borra; esos siete elementos quedan `FIXED_PENDING_VERIFICATION` hasta rescan. Las 836 repeticiones de título son historial de incidencias por fingerprint distinto, no duplicados de identidad.

## Tests

- Pytest: 48 archivos, comportamiento canónico.
- 26 archivos contienen alguna referencia de versión; requieren revisión gradual.
- 537 scripts `check_v*.py` son verificadores históricos, no toda la suite canónica.
- Los checks que fallan únicamente porque exigen un `APP_VERSION` antiguo se clasifican `OBSOLETE/FALSE_POSITIVE_PRONE`; no invalidan una regresión de comportamiento actual.
- Founder-confirmed: topbar, asset único, cache keys y QA probes ya tienen tests permanentes.

## Reports, release y datos

Reports Git: 5.236 antes, 2.039 tras sacar 3.197 evidencias anidadas. Se conservan 2.030 informes raíz porque varios engines los consultan por nombre. El builder canónico excluye `.git`, `.venv`, caches, DB, logs, zips anidados, `browser_qa` y `release_output`. La primera prueba reveló 1,435 GB de capturas dentro del ZIP; después de corregir el builder, el paquete quedó en 29.076.636 bytes, 2.852 archivos, 0 prohibidos y 0 raíces obligatorias ausentes. `reference_images` se conserva porque Product QA/Sentinel y runtime lo consumen de forma activa.

La deuda SQLite y runtime se documenta en [DATA_DEBT_REPORT.md](DATA_DEBT_REPORT.md). No hubo cambio destructivo.

## Config authority

| Categoría | Autoridad |
|---|---|
| Runtime secrets/paths/safe mode | Render env vars |
| Servicios, command, disk y schedule declarativos | `render.yaml`, contrastado con Render MCP |
| Estado real desplegado | Render MCP/runtime SHA |
| Flags operativos | env/DB según contrato específico |
| Producto y rutas | Git `main` + Flask url map |

El `render.yaml` local estaba desalineado: nombres y cron no reflejaban la realidad. Ahora declara `nemesissharkpro`, disco `/data`, master tick `telegram-auto-tick` y Continuous Evolution safe storage. No se cambió infraestructura desde el archivo.

## Métricas before/after previstas

| Métrica | Antes | Después de staging final |
|---|---:|---:|
| Archivos Git | 10.749 | 4.077 |
| CSS Git / activos | 10 / 8 | 8 / 8 |
| JS Git / activos | 7 / 5 | 5 / 5 |
| Templates | 199 | 199 |
| Engines | 157 | 157 |
| Workers | 34 | 34 |
| `app.py` líneas | 29.970 | 29.977 por guard QA, sin refactor estructural |
| Reports Git | 5.236 | 2.042 tras tres documentos canónicos |
| Static assets | 16 | 15 |

Capacidad retirada: 0. Artefactos fuera del índice: 6.674. Asset legacy retirado: 1. Duplicados exactos de fuente retirados: 0; duplicación conductual retirada: 4 handlers y 2 árboles nav muertos.

## Architecture scorecard

Escala prudente basada en evidencia, no en volumen borrado.

| Área | Antes | Después local | Evidencia |
|---|---:|---:|---|
| Ownership | 45 | 61 | mapa de dominios, autoridad visual/config |
| Duplication | 58 | 70 | nav única, 0 source/template duplicates |
| Coupling | 36 | 39 | `app.py` sigue monolítico |
| Legacy control | 30 | 47 | capas clasificadas, shadowing P0 corregido |
| Visual single source | 42 | 72 | tokens + V933 última; compatibilidad aún activa |
| Config single source | 45 | 76 | YAML alineado con realidad conocida |
| Test reliability | 64 | 74 | regresiones nuevas; checks Vxxx aún ruidosos |
| Worker overlap | 40 | 56 | wrappers identificados; entrypoints aún múltiples |
| Runtime cleanliness | 24 | 58 | 6.674 artefactos fuera de Git; `data/runtime` pendiente |

## Top 10 root causes de complejidad

1. `app.py` concentra composición, rutas y helpers de todos los dominios.
2. Cascada CSS histórica activa con alta repetición y especificidad desigual.
3. Stacking contexts entre hermanos que invalidaban z-index internos.
4. Múltiples listeners globales para una misma navegación.
5. Versiones de caché diferentes para el mismo asset.
6. QA generando issues reales durante probes intencionados.
7. Workers nominalmente distintos sobre ejecutores compartidos sin organigrama explícito.
8. 537 verificadores históricos acoplados a versiones.
9. Runtime/evidencia mezclado con código versionado.
10. Configuración declarativa histórica distinta de la infraestructura real.

## Qué parecía basura pero era requerido

Aliases públicos, CSS V928/V930/V936/V937, wrappers de workers y reports raíz con consumidores nominales. Se conservaron.

## Qué fue seguro retirar

Entorno virtual versionado, Browser QA/screenshot/video regenerable, referencias temporales de comparación, navegación muerta, handlers duplicados y el SVG legacy sin referencias.

## Riesgos que quedan

1. Monolito `app.py` y acceso global a estado/DB.
2. 223 selectores CSS cruzados y dependencia de compatibilidad histórica.
3. 316 ficheros runtime todavía versionados y 537 checks Vxxx fuera de una política de retirada.
4. El CSS activo suma aproximadamente 212 KB gzip, 12 KB por encima del presupuesto histórico de 200 KB; los tiempos de ruta P0 pasan, pero el peso de transferencia queda como P1 medible.

## QA final

| Gate | Resultado |
|---|---|
| Pytest completo | 330 PASS, 0 fallos. La regresión de release aislada también pasa 8/8. |
| Local Safe / Mobile LAN | 7/7 PASS |
| `py_compile` / `compileall` | PASS |
| Jinja | 199/199 PASS |
| Imports/routes/static | PASS; 744 rutas del verificador, 0 templates/static ausentes |
| Runtime route map | 807 reglas con `static`; 0 duplicados exactos |
| Routes/links | PASS; 0 unsafe links |
| Smoke | 29/29 PASS |
| Sports P0 | 99 tests PASS; truth, Tier, ranking y consistencia intactos |
| Performance P0 | PASS en rutas y comportamiento; CSS transfer P1 WARNING (212.138 bytes gzip) |
| Privacy / Secret / Rights / Security | PASS; 0 secretos expuestos, 0 cambios de datos reales |
| Continuous Evolution / Master scheduler local | 39 tests PASS |
| Browser QA | 57 capturas, 18 clicks topbar, 8/8 Golden Journeys, 0 JS/page errors, 0 overflow, 0 imágenes rotas, 0 provider calls |
| Viewports | 1366x768, 834x1194 y 390x844 PASS |
| Release builder/audit | 2.852 archivos, 29.076.636 bytes, 0 prohibidos, 0 Browser QA |
| `git diff --check` | PASS |

Las dos advertencias observadas corresponden únicamente a la caché local de pytest bloqueada por ACL de Windows; el `basetemp` aislado evita interferencia en los tests.

## Estado de cierre local

- `OPEN_P0`: 0.
- `OPEN_P1`: 3: aprobación visual Founder de shark/background, reducción futura del payload CSS y rescan de siete issues históricos ya corregidos en intake.
- `TOPBAR`: PASS local con interacción real.
- `SHARK`: FOUNDER_REVIEW_READY, no declarado resuelto.
- `BACKGROUND`: FOUNDER_REVIEW_READY, no declarado resuelto.
- `SPORTS_P0`: PASS local.
- `PERFORMANCE_P0`: PASS; warning P1 de transferencia CSS documentado.
- Capacidad retirada: 0.
- Nuevos costes, proveedores, Stripe o Telegram comercial: 0.
- Commit/push/deploy: no ejecutados porque la plataforma de seguridad exige reconfirmación explícita del fundador para registrar 6.674 retiradas masivas del índice.

## Snapshot de producción durante el cierre

- Producción, GitHub y HEAD previo continúan alineados en `fc743709d6588148285f33a3c783e220bfa86483`.
- `/api/health`, `/api/runtime-version` y `/version`: HTTP 200; `active_errors_count=0`; archivos de versión consistentes.
- Web service: `nemesissharkpro`, deploy `dep-da9v4n710e5c73bd8kj0` live, disco persistente `/data`.
- Master Scheduler: ACTIVE; cron `telegram-auto-tick`, comando real `python tools/render_cron_master_tick.py`, cadencia `*/5 * * * *`.
- Última muestra observada: 30-08-2026 13:05 Madrid; `overall=PASS`, Telegram `PASS/OLD_MATCH`, Continuous Evolution `PASS/SKIPPED_NOT_DUE`.
- Logs de error de web service y cron en la ventana observada: 0.
- Producción todavía no contiene esta consolidación local; no se declara `PRODUCTION_ALIGNED` con el working tree hasta commit, push y auto-deploy.
