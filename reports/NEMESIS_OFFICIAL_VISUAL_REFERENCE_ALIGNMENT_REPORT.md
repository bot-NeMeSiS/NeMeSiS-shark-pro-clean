# NEMESIS DESIGN SYSTEM 1.0 - OFFICIAL REFERENCE ALIGNMENT

## Cierre local vigente - 2026-09-07

> Esta seccion sustituye la decision ejecutiva y las cifras de QA historicas que
> aparecen mas abajo. Se conserva el resto del documento como trazabilidad de
> iteraciones anteriores; no debe interpretarse como evidencia del arbol final.

### Decision ejecutiva

`LOCAL_FUNCTIONAL_PASS / VISUAL_HUMAN_REVIEW_PENDING`

- Base Git: `40e34202d4363b10dcf34bf2e756801c49d85a00`.
- Rama: `main`; base local y `origin/main` iguales al iniciar/cerrar la QA.
- Huella del arbol visual: `2ccf33f687edb94b9e279f9de8597e91ba0ddd1034a21709ebf50d6e69ce401c`.
- Referencias oficiales abiertas y verificadas: `16/16`; hashes preservados `16/16`.
- Produccion no se consulto ni modifico. Este cierre es exclusivamente local.
- No hubo staging, commit, push, PR, merge, deploy, Render, Cron, Telegram ni Stripe.

La app se acerca de forma material a la composicion elegida, pero no se declara
pixel-perfect ni visualmente aprobada. El tiburon es una recreacion original
para NeMeSiS, no el arte original de la referencia, y su semejanza anatomica
permanece pendiente de decision humana.

### Cambios de esta iteracion

- Nuevo tiburon atmosferico original: `static/img/nemesis-shark-atmosphere-v2.webp`.
  Dimensiones `1400x758`, transparencia real, `142528` bytes y SHA-256
  `76961eeb2fa2ab328b5a91e6e31b917903237ae34479c9b96b233fcfd098e60e`.
- Fondo oceanico y presencia del tiburon recompuestos en la autoridad CSS
  existente, sin nueva hoja numerada ni capas interactivas.
- Home desktop reorganizada como columna principal de ruta+partidos y pick
  lateral; el estado sin pick no reserva un hueco vacio.
- Home mobile recompuesta: nombre corto en una linea, nombre largo en dos, y
  producto deportivo visible pronto. Se probaron `390x844` y `430x932`.
- R12 corregida a `/match/m-1` y `templates/match_detail.html`; `/shark` ya no
  se presenta como la referencia de Match Center.
- Directo, Picks e Historico se verificaron por separado en estados
  `POBLADO`, `PARCIAL` y `VACIO`, siempre `SIMULATED_QA` en DB temporal.
- Track Record mobile pasa de tabla comprimida a lista compacta; Telegram
  mobile elimina el gran indicador circular y utiliza estados rectangulares.
- Cache busting visual actualizado mediante `design-system-1-7`.

### Matriz humana conservadora

Los estados siguientes proceden de comparacion fisica. La clasificacion
automatica (`83 MATCH`, `25 MINOR_GAP`) se conserva como metrica tecnica, pero
no sustituye esta lectura ni la aprobacion del fundador.

| Referencia | Superficie real | Estado | Diferencia o limite visible |
|---|---|---|---|
| REF-01 | Admin dashboard | DIFERENCIA VISIBLE | Mismo shell; jerarquia y densidad difieren con datos parciales. |
| REF-02 | Telegram admin | DIFERENCIA VISIBLE | Command Center real; volumen y distribucion no son identicos. |
| REF-03 | Pagos admin | NO COMPARABLE | La referencia esta poblada; no se inventaron ingresos ni estado Stripe. |
| REF-04 | Automatizacion admin | DIFERENCIA VISIBLE | Rail/cabecera coherentes; zona central distribuida de otro modo. |
| REF-05 | Data Marketplace | NO COMPARABLE | Faltan datos reales equivalentes a los de la referencia. |
| REF-06 | Lanzamiento | NO COMPARABLE | El estado real no respalda las metricas representadas. |
| REF-07 | Picks admin | DIFERENCIA VISIBLE | Tabla y auxiliares no replican toda la composicion de referencia. |
| REF-08 | Home desktop/mobile | DIFERENCIA VISIBLE | Grid corregido; el arte del tiburon requiere decision humana. |
| REF-09 | Directo | DIFERENCIA VISIBLE | Tres estados validados; datos y composicion no son identicos. |
| REF-10 | Partidos | DIFERENCIA VISIBLE | Catalogo compacto; densidad y contenido visible difieren. |
| REF-11 | Picks | DIFERENCIA VISIBLE | Tres estados validados sin fabricar metricas no soportadas. |
| REF-12 | Match Center | DIFERENCIA VISIBLE | Emparejamiento correcto; capacidades/datos difieren de la imagen. |
| REF-13 | Track Record | DIFERENCIA VISIBLE | No se fabrica la grafica poblada de la referencia. |
| REF-14 | Membresias | DIFERENCIA VISIBLE | Planes/precios reales; mobile conserva mas detalle. |
| REF-15 | Mi cuenta | DIFERENCIA VISIBLE | Perfil simplificado, sin duplicados; estructura distinta. |
| REF-16 | Telegram cliente | DIFERENCIA VISIBLE | Jerarquia corregida; estado real y composicion difieren. |

`OFFICIAL_SHARK_REFERENCE = PENDIENTE`

`OFFICIAL_BACKGROUND_REFERENCE = PENDIENTE`

No existe ninguna referencia declarada `MATCH JUSTIFICADO` por decision
automatica en este cierre. Las superficies admin mobile son adaptaciones porque
las siete referencias admin no contienen una composicion mobile oficial.

### QA final del ultimo arbol

| Control | Evidencia vigente |
|---|---|
| Suite completa | `469/469 PASS` sobre DB local aislada; proveedores/jobs desactivados |
| Suite focal visual/Sports/Context | `147/147 PASS` |
| Matriz navegador | `108` capturas, `9` viewports, `54` clicks/taps, `9/9` journeys |
| Componentes | `1103` instancias; `0` fallos y `0` overflow |
| Colisiones / imagenes / JS | `0 / 0 / 0` |
| Technical copy leaks | `0` |
| Proveedores durante Browser QA | `0` llamadas |
| Jinja | `199/199 PASS` |
| Imports/rutas/static | `744` rutas GET; `0` templates o assets ausentes |
| Smoke Flask | `29/29 PASS`; `0` respuestas 5xx |
| Privacy/Secret Guard | `1104` archivos; `0` hallazgos; valores no impresos |
| Sports lifecycle | `V937 SPORTS LIFECYCLE CHECK: OK` |
| py_compile / compileall | PASS / PASS |
| git diff --check | PASS |

El auditado de presentacion encontro `21` enlaces directos a APIs internas/admin,
deuda ya conocida de UX. No son enlaces vacios ni una fuga de autorizacion:
`empty href=0`, `javascript:void=0`, formularios sin accion segura `0`.

### Incidencias de ejecucion conservadas

La primera suite completa de esta iteracion se ejecuto con la frontera HTTP de
`NEMESIS_LOCAL_SAFE_MODE`; siete tests que deben autenticar endpoints simulados
recibieron correctamente `403`. Repetidos en DB temporal, red/proveedores/jobs
desactivados y sin esa frontera incompatible: `7/7 PASS`; suite completa final
`469/469 PASS`. No se clasifica como regresion de producto.

Los cuatro fallos anunciados por la pasada focal fueron:

| ID | Causa | Correccion |
|---|---|---|
| `PQA-ED8959CCFDF0` | Se evaluo consistencia temporal cruzada sin varias superficies comparables. | `observed=False` queda `NOT_RUN`; los fallos realmente observados siguen fallando. |
| `PQA-5F51BB30AC17` | Home no estaba capturada y `NOT_OBSERVED` del tiburon abrio issue. | El detector exige observacion; la matriz final captura Home y conserva revision humana. |
| `PQA-07BE1203FCBA` | La misma ausencia de Home genero un falso fallo de fondo. | Estado observado explicito y evidencia transversal real. |
| `PQA-C813412FDC80` | Defaults `ratio=0`/`first_viewport=None` se trataron como densidad observada. | La densidad solo se decide con captura; el caso incorrecto observado mantiene test. |

El resultado historico `PQA-20260907123456 = FAIL` no se borra ni se reescribe.

### Rendimiento y preservacion

- CSS rastreado: baseline HEAD `216492` bytes gzip; candidato `218471` bytes
  gzip; delta `+1979` bytes, dentro del margen local de 2 KiB.
- Asset atmosferico nuevo: `142528` bytes; no video, WebGL ni peticion remota.
- Contratos protegidos verificados por hash: `10/10` intactos.
- `SPORTS_DATA_LIVE_CERTIFICATION.md` y DAY 3 intactos, SHA-256
  `3E4C63AC8AB798F363E24DE0B250E7996A5851B0C4B8C59088F1490D1F298444`.
- Sports Truth, Match Context, Madrid Time, reutilizacion por peticion y
  aislamiento entre usuarios quedan cubiertos por la suite final.
- Esta QA no certifica cobertura deportiva real, proveedor, LIVE Tier S/A ni
  produccion. `REAL_SPORTS_CERTIFICATION` conserva su estado independiente.

### Evidencia privada vigente

- Matriz final y 108 capturas:
  `.tmp_reference_review/visual_definitive_20260907/final_reference_matrix_v2/PQA-20260907151138/`
- Poblado final:
  `.tmp_reference_review/visual_definitive_20260907/final_populated_tree/PQA-20260907151528/`
- Vacio final:
  `.tmp_reference_review/visual_definitive_20260907/final_empty_tree/PQA-20260907151838/`
- Home 430 con nombre corto:
  `.tmp_reference_review/visual_definitive_20260907/final_home_430_short_v2/PQA-20260907151750/`
- Comparativas focales legibles:
  `.tmp_reference_review/visual_definitive_20260907/visual_review/`
- Paquete privado final, sin comprimir:
  `.tmp_reference_review/visual_definitive_20260907/founder_package_final_20260907/`

El paquete final contiene `103` archivos: `33` comparativas, `3` laminas de
estados, `34` capturas individuales y copias byte a byte de las `16` referencias.
Su manifiesto contiene `102` entradas y se verifico con `0` diferencias y `0`
archivos de DB, logs, credenciales o secretos. La compresion ZIP fue rechazada
por la politica del entorno; no se intento eludirla.

### Estado de entrega

`CANDIDATO_LOCAL_FUNCIONAL = PASS`

`COMPARACION_VISUAL = COMPLETADA_CON_DIFERENCIAS_VISIBLES`

`REVISION_HUMANA = PENDIENTE`

`STAGING / COMMIT / PUSH / DEPLOY = NO`

---

## Evidencia historica previa (superada por el cierre vigente)

## Decision ejecutiva

`LOCAL_IMPLEMENTATION_PASS`

NeMeSiS ha migrado la presentacion activa a una autoridad visual comun derivada
de las 16 PNG oficiales. La migracion preserva Sports Truth, Sports P0,
Performance P0 y los contratos funcionales existentes.

Los estados visuales no se autoaprueban:

- `OFFICIAL_SHARK_REFERENCE`: `FOUNDER_REVIEW_REQUIRED`.
- `OFFICIAL_BACKGROUND_REFERENCE`: `FOUNDER_REVIEW_REQUIRED`.
- `VISUAL_FALSE_PASS_RECURRENCE`: conservado como contrato permanente.
- `ASSET_LOADED`: PASS tecnico; no equivale a aprobacion visual.

No se copiaron instaladores, payloads, codigo, templates ni CSS de
`REFERENCE_ONLY`. Las referencias se usaron exclusivamente como evidencia
visual de solo lectura.

## Referencias oficiales

Referencias abiertas y analizadas fisicamente: `16/16`.

| ID | Archivo | Familia |
|---|---|---|
| REF-01 | `admin/reference_import_v900_01.png` | Dashboard admin |
| REF-02 | `admin/reference_import_v900_02.png` | Telegram admin |
| REF-03 | `admin/reference_import_v900_03.png` | Pagos y membresias admin |
| REF-04 | `admin/reference_import_v900_04.png` | Automatizacion |
| REF-05 | `admin/reference_import_v900_05.png` | Data Marketplace |
| REF-06 | `admin/reference_import_v900_06.png` | Lanzamiento y operaciones |
| REF-07 | `admin/reference_import_v900_07.png` | Picks y partidos admin |
| REF-08 | `client/reference_import_v900_08.png` | Home desktop/mobile |
| REF-09 | `live/reference_import_v900_09.png` | Directo desktop/mobile |
| REF-10 | `calendar/reference_import_v900_10.png` | Partidos y calendario |
| REF-11 | `picks/reference_import_v900_11.png` | Picks SHARK |
| REF-12 | `shark/reference_import_v900_12.png` | Match Center y SHARK |
| REF-13 | `track-record/reference_import_v900_13.png` | Track Record |
| REF-14 | `memberships/reference_import_v900_14.png` | FREE, PRO y ELITE |
| REF-15 | `profile/reference_import_v900_15.png` | Perfil y cuenta |
| REF-16 | `telegram/reference_import_v900_16.png` | Telegram cliente |

Manifest reproducible: `reference_images/reference_manifest.json`.

## Design DNA extraido

- Base azul-negro de oceano con profundidad radial y luz cian localizada.
- Bruma, particulas y vineta sutiles; lectura protegida por overlay oscuro.
- Tiburon de marca compacto y tiburon atmosferico como contratos separados.
- Cards densas, radios moderados, bordes finos y glow localizado.
- Datos deportivos antes que explicacion, SHARK antes que betting.
- Topbar cliente compacta; admin mas denso y operativo.
- Mobile compuesto expresamente con bottom navigation y safe areas.

## Autoridad visual canonica

La implementacion evita una nueva hoja final paralela. La autoridad activa se
consolida en:

- `static/v933_design_tokens.css`: tokens de color, tipografia, espacio,
  radios, sombras y capas.
- `static/v933-product.css`: shell, fondo, tiburones, cards, densidad y
  responsive canonico.
- `static/img/nemesis-shark-brand.svg`: marca compacta sin caja heredada.
- `static/img/nemesis-shark-atmosphere.svg`: silueta atmosferica lateral con
  geometria, aletas, mandibula, branquias, cuerpo y cola diferenciados.
- `templates/base.html`: orden de carga y versionado estatico.

El selector heredado que aplicaba borde, radio y sombra a la imagen del logo
fue neutralizado en la autoridad canonica. La comprobacion computada final
confirma `border: 0`, `border-radius: 0`, `box-shadow: none` y fondo
transparente.

## Identidad de competiciones

Se corrigio la causa raiz de las colisiones Primera/Segunda y de identidades
ambiguas:

- ID canonico antes que alias.
- Alias normalizado exacto antes que fallback seguro.
- Sin clasificacion por substring generico.
- Segunda Division usa su identidad canonica independiente.
- Los upserts deportivos actualizan `competition_key` de forma consistente.
- El mismo contrato se entrega a Home, Partidos, Directo, Calendar, Match,
  Team, Player, Competition, Picks y SHARK.

La regresion queda cubierta por `tests/test_competition_identity_regression.py`.

## Sistema de dos tiburones

`BRAND_SHARK`

- Silueta reconocible a 32-48 px.
- Sin avatar, recuadro ni panel decorativo.
- Uso exclusivo de branding y topbar.

`ATMOSPHERIC_SHARK`

- Geometria lateral propia alineada con la familia de referencias.
- Presencia grande, luminosa e integrada en el oceano.
- Crop y opacidad especificos para desktop, tablet y mobile.
- Capas decorativas con `pointer-events: none`.

La geometria se modifico realmente; no se resolvio solo mediante opacidad o
transformaciones CSS.

## Fondo oficial

La composicion activa usa capas diferenciadas:

1. Near-black navy base.
2. Profundidad azul radial.
3. Fuente de luz cian localizada.
4. Bruma y textura submarina sutil.
5. Tiburon atmosferico.
6. Vineta y overlay de legibilidad.
7. Shell y contenido.

No utiliza video ni imagen raster pesada. Se respeta
`prefers-reduced-motion` y no se introdujo procesamiento visual durante el
render del servidor.

## QA visual 2.0

El inspector existente fue ampliado en lugar de crear otro worker decorativo.
Ahora pondera estructura visible y no presencia de archivos:

- silueta y presencia del tiburon;
- composicion del fondo;
- primer viewport;
- densidad de cards;
- navegacion real;
- identidad de competicion;
- colisiones texto-borde, clipping y overflow;
- estructura mobile a 360 px.

Viewports certificados:

- 1440x900
- 1366x768
- 1024x768
- 834x1194
- 768x1024
- 430x932
- 390x844
- 375x812
- 360x800

Resultado full final local:

- 171 capturas reales.
- 54 clicks/taps reales.
- 9/9 golden journeys.
- 0 issues P0/P1.
- 0 errores JavaScript o de pagina.
- 0 llamadas a proveedores deportivos.
- 20 contratos permanentes PASS.
- 3 contratos visuales `FOUNDER_REVIEW_REQUIRED`.

La Quality Division mantiene `VISUAL = WARNING` hasta la decision humana.

## Matriz final local

| Familia | Estado visual | Decision humana |
|---|---|---|
| Background | FOUNDER_REVIEW_REQUIRED | PENDING |
| Brand Shark | FOUNDER_REVIEW_REQUIRED | PENDING |
| Atmospheric Shark | FOUNDER_REVIEW_REQUIRED | PENDING |
| Client shell | FOUNDER_REVIEW_REQUIRED | PENDING |
| Home | FOUNDER_REVIEW_REQUIRED | PENDING |
| Partidos | FOUNDER_REVIEW_REQUIRED | PENDING |
| Directo | FOUNDER_REVIEW_REQUIRED | PENDING |
| Match Center | FOUNDER_REVIEW_REQUIRED | PENDING |
| Team Center | FOUNDER_REVIEW_REQUIRED | PENDING |
| Competition Center | FOUNDER_REVIEW_REQUIRED | PENDING |
| Player Center | FOUNDER_REVIEW_REQUIRED | PENDING |
| Picks | FOUNDER_REVIEW_REQUIRED | PENDING |
| SHARK | FOUNDER_REVIEW_REQUIRED | PENDING |
| Track Record | FOUNDER_REVIEW_REQUIRED | PENDING |
| Telegram | FOUNDER_REVIEW_REQUIRED | PENDING |
| Memberships | FOUNDER_REVIEW_REQUIRED | PENDING |
| Account | FOUNDER_REVIEW_REQUIRED | PENDING |
| Admin/Founder/Growth | FOUNDER_REVIEW_REQUIRED | PENDING |
| Desktop | FOUNDER_REVIEW_REQUIRED | PENDING |
| Tablet | FOUNDER_REVIEW_REQUIRED | PENDING |
| Mobile 360-430 | FOUNDER_REVIEW_REQUIRED | PENDING |

La QA no detecta fallos funcionales, colisiones ni gaps estructurales P0/P1.
La equivalencia estetica sigue reservada a la revision del fundador.

## QA funcional y seguridad

- Full `pytest`: 371/371 PASS en 52 archivos de pruebas.
- `py_compile`: PASS.
- `compileall`: PASS.
- Jinja/imports/routes/static: PASS; 744 rutas, 0 assets/templates ausentes.
- Route/link audit: PASS; 807 rutas, 0 enlaces inseguros en smoke.
- Smoke real Flask: PASS; 29 rutas, 0 fallos.
- Privacy/Secret Guard: PASS; 1.099 archivos, 0 secretos o privacidad.
- Performance P0: PASS; SHARK median 32.3 ms, P95 67.2 ms, 0 external,
  0 writes.
- Launch readiness: PASS.
- Sports P0 y verdad LIVE: PASS, sin llamadas extra a proveedor.
- Fake data introducida: 0.
- Telegram enviado: 0.
- Stripe: 0.
- Nuevo coste: 0.

## Rendimiento CSS

- Baseline estable gzip: 215.311 bytes.
- Design System 1.0 gzip: 215.563 bytes.
- Delta de migracion: +252 bytes.
- Regresion de presupuesto: PASS, dentro de 2 KB.
- Objetivo historico de 200 KB: WARNING pendiente; no se ha sacrificado el
  diseno ni se ha eliminado legacy sin evidencia para forzar el numero.

## Evidencia local

- Full QA final: `browser_qa/DESIGN_SYSTEM_1_RELEASE/`.
- Logo final sin caja: `browser_qa/DESIGN_SYSTEM_1_LOGO_FINAL/`.
- Comparativas de referencia y producto: `data/local_dev/visual_review/`.

Las capturas son de la aplicacion real, no mockups ni imagenes generadas.

## Estado de cierre local

- Functional regressions: 0.
- Broken buttons: 0.
- Broken links: 0.
- Mojibake: 0.
- Broken images: 0.
- Overflow/collisions: 0 en nueve viewports.
- Client/admin leaks: 0.
- Fake data: 0.
- Provider calls extra: 0.
- New spend: 0.

`DESIGN_SYSTEM_1_LOCAL = PASS`

`SPORTS_P0 = PASS`

`VISUAL_FOUNDER_APPROVAL = PENDING`

No se debe registrar `RESOLVED` para tiburon o fondo hasta que el fundador
apruebe las comparativas reales.
