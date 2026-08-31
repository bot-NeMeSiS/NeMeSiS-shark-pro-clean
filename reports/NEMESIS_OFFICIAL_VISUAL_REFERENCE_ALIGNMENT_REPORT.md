# NEMESIS DESIGN SYSTEM 1.0 - OFFICIAL REFERENCE ALIGNMENT

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

| Familia | Estado tecnico | Decision humana |
|---|---|---|
| Background | MATCH | FOUNDER_REVIEW_REQUIRED |
| Brand Shark | MATCH | FOUNDER_REVIEW_REQUIRED |
| Atmospheric Shark | MATCH | FOUNDER_REVIEW_REQUIRED |
| Client shell | MATCH | FOUNDER_REVIEW_REQUIRED |
| Home | MATCH | FOUNDER_REVIEW_REQUIRED |
| Partidos | MATCH | FOUNDER_REVIEW_REQUIRED |
| Directo | MATCH | FOUNDER_REVIEW_REQUIRED |
| Match Center | MATCH | FOUNDER_REVIEW_REQUIRED |
| Team Center | MATCH | FOUNDER_REVIEW_REQUIRED |
| Competition Center | MATCH | FOUNDER_REVIEW_REQUIRED |
| Player Center | MATCH | FOUNDER_REVIEW_REQUIRED |
| Picks | MATCH | FOUNDER_REVIEW_REQUIRED |
| SHARK | MATCH | FOUNDER_REVIEW_REQUIRED |
| Track Record | MATCH | FOUNDER_REVIEW_REQUIRED |
| Telegram | MATCH | FOUNDER_REVIEW_REQUIRED |
| Memberships | MATCH | FOUNDER_REVIEW_REQUIRED |
| Account | MATCH | FOUNDER_REVIEW_REQUIRED |
| Admin/Founder/Growth | MATCH | FOUNDER_REVIEW_REQUIRED |
| Desktop | MATCH | FOUNDER_REVIEW_REQUIRED |
| Tablet | MATCH | FOUNDER_REVIEW_REQUIRED |
| Mobile 360-430 | MATCH | FOUNDER_REVIEW_REQUIRED |

`MATCH` en esta tabla significa que no queda un gap tecnico demostrado por la
comparacion y la QA local. No sustituye la aprobacion estetica del fundador.

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

- Full QA: `browser_qa/DESIGN_SYSTEM_1_FINAL/`.
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
