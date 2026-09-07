# NEMESIS DESIGN SYSTEM 1.0 - OFFICIAL REFERENCE ALIGNMENT

## Autorizacion limitada: expectativa de Favoritos (vigente)

Operacion local posterior a la ampliacion global. Estado global: **PARCIAL**.
No se ha cambiado la interfaz ni se ha repetido la matriz de navegador.

Conciliacion Git: la primera lectura vio `7fa7b7ac241295da666921ea9f50f6f632804ce1`.
Antes del manifiesto y de la reproduccion aparecio el commit externo
`936cdc8863fba3fc967a2eeaf6b65750767766d0`, hijo directo del anterior, que incorpora
los 23 archivos del candidato previo. No fue creado por esta operacion. Esta es
la base de la reproduccion y de la suite final. Los 22 archivos de producto/tests
de ese candidato conservan exactamente sus hashes; el informe es el unico que
se actualiza documentalmente aqui. No se consulto ni modifico produccion.
El HEAD y el indice permanecen iguales desde el manifiesto previo a las pruebas.

### Identificacion y prueba previa

- Archivo: `tests/test_product_excellence_sprint_02.py`, linea 49.
- Test: `tests/test_product_excellence_sprint_02.py::test_product_excellence_sprint_02_top100_markers_are_present`.
- Literal anterior: `Crea tu primer favorito`.
- Literal autorizado y aplicado: `Guarda lo que sigues`.
- Productor: `templates/favorites.html`, encabezado de ayuda dentro de
  `details.ns-favorites-help`; este template no se modifico en esta operacion.
- Motivo: conserva la invitacion a guardar equipos, competiciones o partidos;
  elimina la suposicion incorrecta de que quien consulta la ayuda no tiene
  favoritos. El resumen sigue siendo `Añadir favoritos` y las instrucciones
  siguen explicando seleccion, estrella/alta manual y regreso al radar.

Diff completo autorizado del test:

```diff
-            "Crea tu primer favorito",
+            "Guarda lo que sigues",
```

No se agregaron alternativas, expresiones amplias, omisiones, cambios de umbral
ni nuevos PASS artificiales. Los demas literales, marcadores, assert y pruebas
permanentes conservan contenido. Se verifico igualdad exacta del archivo anterior
tras esa unica sustitucion, incluidos sus finales de linea originales.

Antes de editar se reprodujeron 14 tests: 13 PASS y el unico fallo esperado en
ese literal. Las regresiones de ayuda poblada/vacia y aislamiento no fallaron.
Un probe adicional SIMULATED_QA renderizo el template real con listas coherentes:
18/18 comprobaciones de encabezado y guia, formulario existente, enlaces calendario
y partido, destino de alta manual, retirada, datos visibles, ausencia de falso
vacio con favoritos, vacio honesto, redireccion anonima y consultas por user_id.
Es una comprobacion local de render/contratos, NO clicks ni una nueva certificacion
completa de permisos. No escribio DB de negocio ni ejecuto acciones externas.

La revision de seguridad normal permitio la operacion tras esta autorizacion;
no se eludio el bloqueo anterior. Copia, hashes y evidencia antes/despues:
`.tmp_reference_review/favorites_copy_authorization/`.

### Validacion de esta operacion

- Grupo focal posterior: **24/24 PASS**, 0 fallos y 0 omitidos; incluye el fichero
  afectado, comportamiento visual, dashboard/aislamiento y validacion de rutas.
- Suite completa unica de cierre: **477/477 PASS**, 0 fallos, 0 errores y 0
  omitidos. XML: `.tmp_reference_review/favorites_copy_authorization/full_final.xml`.
- `git diff --check`: PASS. La unica modificacion de prueba es la sustitucion
  literal de una linea; el resto de cambios de esta operacion son este informe
  y evidencias locales privadas. Sin staging, commit, push, PR, merge ni deploy.
- Jinja: 199 plantillas. Red externa bloqueada; jobs apagados; secretos externos
  vacios y credenciales sinteticas de prueba. No navegador concurrente.
- No se cambian los resultados historicos de las suites anteriores.

### Correccion de atribucion y pendientes globales

Los dos 500 de la pasada global quedan como **ORIGEN PREEXISTENTE NO CONFIRMADO**.
La ausencia de cambios en sus ficheros no demuestra una reproduccion equivalente
contra el baseline protegido. No se realizo ahora esa comparacion ni una nueva
ejecucion de las rutas; se conserva exclusivamente la evidencia ya disponible.

| Ruta | Evidencia y condiciones observadas | Estado |
| --- | --- | --- |
| `/admin/telegram-audit` | HTTP 500 a 390x844 y 1366x768, ADMIN de prueba, DB local y escenario poblado SIMULATED_QA. UndefinedError de Jinja: `audit` no definido. El handler entrega `data.telegram_diagnostics`, pero el template lee `audit.counts/checks/settings`. | PENDIENTE; origen preexistente no confirmado |
| `/admin/retention-center` | HTTP 500 en ambos anchos y mismo tipo de entorno. `jinja2.exceptions.UndefinedError: 'retention' is undefined`. El handler entrega `data.retention`; el template exige variable superior y campos de score no construidos por ese handler. | PENDIENTE; origen preexistente no confirmado |

Fuente: `.tmp_reference_review/consolidated_h01_h09/global_final_matrix/evidence.json`,
resumen global conservado y trazas observadas. El recorrido usaba reloj fijo
2026-09-07T16:00:00+02:00, con desplazamiento de segundos por viewport registrado
en cada fila. No certifica el comportamiento de produccion.

Las ocho observaciones incompletas permanecen **NOT_RUN / TimeoutError**:

| Ruta | Viewport | Motivo registrado |
| --- | --- | --- |
| `/admin/company-audit` | 390x844 | Navegacion excedio 15000 ms |
| `/admin/auto-improvement` | 390x844 | Navegacion excedio 15000 ms |
| `/admin/codex-automation` | 390x844 | Navegacion excedio 15000 ms |
| `/admin/team-identity` | 390x844 | Navegacion excedio 15000 ms |
| `/admin/not-found-events` | 390x844 | Navegacion excedio 15000 ms |
| `/admin/codex-automation` | 1366x768 | Navegacion excedio 15000 ms |
| `/admin/team-identity` | 1366x768 | Navegacion excedio 15000 ms |
| `/admin/not-found-events` | 1366x768 | Navegacion excedio 15000 ms |

La carrera de stat() de temporales observada en Codex Automation es una pista
local adicional, no una causa demostrada para los ocho timeouts. No equivalen
a una caida productiva ni se convierten en PASS.

Las **15 familias sin recorrido** en la matriz global siguen pendientes:

| Familia | Rutas representativas | Limite registrado |
| --- | --- | --- |
| highlight_detail / resource_unavailable | `/highlight/<highlight_id>`, `/resumen/<highlight_id>` | Entidad de prueba requerida |
| password_reset_form | `/reset-password/<token>`, `/admin-reset-password/<token>` | Contexto/token de prueba requerido |
| local_safe_portal | `/local-safe` | Contexto/accion por revisar |
| admin_bootstrap | `/admin-bootstrap` | Accion de inicializacion excluida |
| admin_sportsdb_sync | `/admin/sportsdb-sync` | Limite de sincronizacion |
| admin_sportsdb_feed | `/admin/sportsdb-feed` | Limite de sincronizacion |
| admin_matches_sync | `/admin/matches`, `/admin/matches-sync` | Limite de sincronizacion |
| admin_telegram | `/admin/telegram` | Sincroniza suscriptores; no ejecutada |
| admin_automation | `/admin/automation` | Ejecucion automatica excluida |
| admin_data_center | `/admin/data-center` | Scheduler/sincronizacion excluidos |
| admin_api_sports_audit | `/admin/api-sports`, `/admin/api-sports-audit` | Sincronizacion de fixtures/LIVE excluida |
| admin_sentinel_workflow | `/admin/sentinel-workflow` y aliases | Ciclo Sentinel excluido |
| admin_visual_worker | `/admin/visual-worker` y aliases | Worker excluido |
| admin_sentinel_autopilot | `/admin/sentinel-autopilot` y aliases | Escaneo con acciones por revisar |
| admin_track_record | `/admin/track-record` | Grading excluido |

El inventario completo conserva todos los aliases en
`.tmp_reference_review/global_coverage/final_family_matrix.json`. Ademas siguen
pendientes los roles/estados e interacciones no probados por familia, la comparacion
artistica global y la aprobacion humana de tiburon/fondo. Nada de ello se resuelve
por actualizar la frase de un test. Los 500 quedan para un encargo separado.

## Ampliacion global de experiencia - 2026-09-07 (vigente, LOCAL PARCIAL)

Este apartado prevalece para el alcance global. No declara toda la aplicacion
aprobada, ni certifica produccion. Conserva el cierre H01-H09 inferior como
historial y evidencia previa, sin reutilizar sus cifras como QA del arbol nuevo.

### Base, preservacion y limites

- HEAD: `7fa7b7ac241295da666921ea9f50f6f632804ce1`; indice vacio, sin cambios de rama.
- Los 20 archivos del candidato H01-H09 se conservaron antes de ampliar el trabajo:
  `.tmp_reference_review/global_coverage/baseline/manifest.json` y copias selectivas.
- `app.py`, Sports Truth y `SPORTS_DATA_LIVE_CERTIFICATION.md` DAY 3 conservan
  sus hashes anteriores. Match Context y aislamiento de usuarios no se editaron.
- Las 16 PNG oficiales se reabrieron en cuatro contactos y conservan sus hashes.
  R12 corresponde a Match Center; no se usa como contrato de la pantalla SHARK.
- No se regeneraron tiburon, fondo ni referencias. Sin nueva capa CSS, datos,
  funcionalidad, precios o cambios financieros. H03 permanece separado del estilo.
- Sin staging, commit, push, PR, merge, deploy ni consultas de produccion/Render.
  Sin proveedores, cron, pagos, usuarios reales ni envios Telegram.

### Inventario global y matriz completa

Se inventariaron **160 handlers HTML**, agrupados en **146 familias estaticas de
templates**. El inventario conserva aliases, componentes incluidos, decoradores,
ruta, fichero y linea. Se seleccionaron **131 GET HTML representativos** tras
excluir acciones, sincronizaciones y rutas que necesitan contexto adicional.

La matriz detallada de TODAS las familias esta en
`.tmp_reference_review/global_coverage/final_family_matrix.json`; su version
legible y las comparativas estan en `.tmp_reference_review/global_coverage/index.html`.
Son evidencias privadas locales, no otro centro de control ni un paquete de release.

Cada fila distingue rutas/aliases, template real renderizado, componentes, rol,
viewport, HTTP, destino final y captura. Los aliases compartidos no se consideran
journeys probados individualmente. Se uso cliente PRO de prueba, ADMIN de prueba
y anonimo: FREE/ELITE/ELITE+ no quedan certificados por este recorrido PRO.
Tampoco la presencia de un template equivale a una comprobacion de sus acciones.

| Cobertura | Resultado y limite |
| --- | --- |
| Transversal poblado | 262 observaciones, 131 representantes x escritorio 1366x768 y movil 390x844. |
| Layout automatico | 250 observaciones sin overflow global, cabecera cubierta ni colision de marcador detectada. No es fidelidad visual ni prueba de todos los botones. |
| Errores locales | 4 respuestas 500, correspondientes a dos familias en ambos anchos; detalle inferior. |
| Esperas agotadas | 8 observaciones NOT_RUN en cinco familias operativas. Nunca contadas como PASS. |
| JS | 0 page_errors capturados en este recorrido; acciones no ejecutadas siguen pendientes. |
| Focal de cambios | 30 capturas de 10 familias a 360/390/1366, mas 10 tablet 834x1194; sin fallos del detector ni page_errors. |
| H01-H09 reejecutado | 28 vistas a 390/1366, sin fallos; controles positivos/negativos del detector y ampliacion de texto Match. |
| Estados parcial/vacio | 5 vistas por estado, a 390: Home, Match, Membresias, Telegram e Historico. No extrapolados al resto de familias. |
| Referencia y arte | Comparacion humana/IA acotada, no MATCH global. H07 y aprobacion de fondo/tiburon siguen pendientes. |
| Produccion | NOT_RUN; ninguna de estas capturas procede de produccion. |

Los timeouts afectan Company Audit, Auto Improvement, Codex Automation,
Team Identity y Not Found Events. Algunos recorren el arbol local completo;
los perfiles temporales del navegador provocaron ademas una carrera de stat()
en Codex Automation. No se ha declarado caida productiva ni se han activado jobs.
Las familias excluidas por acciones/contexto y las restantes sin comparacion
individual mantienen PENDIENTE, no PASS por herencia de CSS.

### Cambios compartidos y consumidores

| Componente | Cambio real | Consumidores |
| --- | --- | --- |
| Heroes semanticos | Titulos compactos y espaciado consistente; precedencia acotada frente a V827-V837. | Acceso, Favoritos, Soporte, Observabilidad y otras vistas con hero directo bajo el shell. No todos los heroes personalizados. |
| Navegacion operativa | Flex con etiquetas completas; desplazamiento horizontal movil en lugar de cortar palabras. | Vistas con admin-menu, incluida Observabilidad. |
| Metricas operativas | Cuatro columnas desktop, dos movil; metric deja de ser otra tarjeta dentro de la tarjeta. | Admin grid.compact-grid y card > metric. |
| Acceso local | Separacion de aviso LOCAL y cabecera auth a movil; formulario y recuperacion preservados. | Acceso cliente/admin y familia auth. |
| Favoritos | Ayuda desplegable, cerrada cuando ya hay favoritos; contenido deportivo visible antes. | favorites.html y aliases. Formularios y destinos originales intactos. |
| Entidades | Identidad compacta, acciones agrupadas y metadatos en dos columnas movil. | Team, Competition y Player con las clases canonicas existentes. |
| QA | Inventario de templates corregido; anonimo realmente sin cookie; registro de template/destino/NOT_RUN; tablet explicita. | Herramientas locales existentes, sin nuevos motores. |

Los !important nuevos se limitan a propiedades con una regla legacy ganadora
demostrada mediante estilos calculados: titulos, columnas de KPI, decoracion de
metricas y padding del acceso local. No se hizo una purga global ni otra hoja CSS.

### Dependencias funcionales encontradas, NO ocultadas

1. `/admin/telegram-audit`: el handler entrega `data.telegram_diagnostics`, pero
   el template exige `audit.counts`, `audit.checks` y `audit.settings`; se reproduce
   UndefinedError y 500. No se relleno con ceros ni se activo Telegram.
2. `/admin/retention-center`: entrega `data.retention`, mientras el template exige
   `retention.global_score` y otros campos que el handler no construye. Se reproduce
   `retention is undefined`; no se inventaron scores para completar el dashboard.

Ambos handlers y templates no se editaron en el incremento visual, pero no se
comparo el baseline protegido bajo las mismas condiciones. Clasificacion corregida:
**ORIGEN PREEXISTENTE NO CONFIRMADO**. Son dependencias funcionales pendientes;
no se atribuyen al CSS ni se descartan como ausencia normal de datos. Requieren
reconciliar su contrato en un cambio separado y probado.

### QA del arbol y trazabilidad

- Jinja: 199 templates compilados en esta ejecucion.
- Pruebas focales: 20/20 (formularios, favoritos, temporal y Match Center).
- Primera suite completa: 477 tests, 475 pasados y 2 fallidos, sin omitidos.
  Un fallo es una carrera de inventario de temporales con el navegador concurrente.
  El otro exige literalmente `Crea tu primer favorito`, texto sustituido por
  `Guarda lo que sigues` para no dar instrucciones falsas a quien ya tiene favoritos.
- El intento de actualizar esa expectativa fue bloqueado por la revision de
  seguridad. NO se modifico el test ni se elimino el check. La nueva prueba de
  comportamiento comprueba ayuda abierta sin favoritos, cerrada con favoritos,
  formulario conservado y contenido deportivo fuera del desplegable.
- Reejecucion serial completa: **477 tests, 476 pasados, 1 fallido, 0 omitidos**.
  El inventario pasa sin navegadores concurrentes. Persiste unicamente la
  expectativa literal antigua de favoritos; no se sustituye por un PASS.
  Evidencia: `.tmp_reference_review/global_coverage/pytest_serial.xml`.
- `compileall` de las herramientas y test modificados: PASS. `git diff --check`:
  PASS, con avisos informativos de normalizacion LF/CRLF, no errores del diff.
- Huella visual del recorrido final:
  `85c2c7d90fe1ca396b914e7c3267a74665e2e52c8534125ad52b52715294d62a`.
- Evidencia: `global_final_matrix/evidence.json`, `global_core_regression/evidence.json`,
  `global_focal_verified/evidence.json`, `global_tablet_verified/evidence.json`,
  `global_partial_verified/evidence.json` y `global_empty_verified/evidence.json`
  bajo `.tmp_reference_review/consolidated_h01_h09/`.
- Fixtures exclusivamente SIMULATED_QA; DB de prueba, credenciales externas vacias,
  jobs desactivados y red externa bloqueada. La suite registro 0 intentos externos.
  Se bloqueo tambien `/api/live` en el navegador. No se ha medido coste del sistema
  existente; esta ejecucion no contrato servicios ni inicio gasto o proveedores.

### Comparacion artistica y decision

Home conserva una franja LIVE mas alta y menor densidad inicial que R08, en parte
por priorizar el deporte y una muestra pequena. No se rellena con partidos falsos.
Match R12 difiere en escala de escudos, jerarquia y presencia del tiburon; no se
copian porcentajes, cuotas o analisis de la referencia. Company OS y otras vistas
legacy conservan estructuras propias y quedan PARCIALES. El tiburon sigue siendo
geometricamente distinto de las PNG; no se ha reinterpretado ni regenerado aqui.

El paquete incluye referencia frente a captura final y diez antes/despues reales,
con origen SIMULATED_QA y escalado proporcional explicito. No son mockups.

**Decision: candidato LOCAL PARCIAL, no aprobacion global.** H01-H09 se conserva;
H07 artistico pendiente. Quedan por resolver los contratos de las dos vistas admin,
completar la validacion textual posterior registrada al inicio y completar las familias,
roles, estados e interacciones pendientes. No publicar este resultado como QA global PASS.

## Cierre consolidado H01-H09 - 2026-09-07 (historico preservado)

Esta seccion prevalece sobre los cierres historicos siguientes. Alcance LOCAL;
no certifica produccion ni aprueba artisticamente tiburon o fondo.

- Base real: `7fa7b7ac241295da666921ea9f50f6f632804ce1` (arbol limpio al inicio).
  Los candidatos anteriores ya estaban incluidos en ese commit externo; no se restauraron.
- Huella visual final: `96776bc8ead87b199b9067d3ed7df473a17f230ded5d74a7c1f6797c49cf5d10`.
- Preservacion selectiva: `.tmp_reference_review/consolidated_h01_h09/baseline/manifest.csv`.
- `app.py`, Sports Truth, `SPORTS_DATA_LIVE_CERTIFICATION.md` DAY 3 y el asset
  atmosferico conservan contenido. Las 16 referencias conservan sus hashes.
- Sin staging, commit, push, PR, merge, deploy, consultas de produccion o cambios remotos.

### Hallazgos y resolucion

| ID | Estado | Causa, correccion y prueba |
| --- | --- | --- |
| H01 | RESUELTO CON PRUEBA | El score absoluto a top 61% invadia la fecha. Ahora hay un unico marcador dentro del flujo de la cabecera. La regla legacy V858 `[class*="status"]` convertia toda la zona en un circulo: se anula solo en esta zona. Rectangulos reales Range para score/estado/fecha; controles correcto, solapado y circulo legacy. FT, LIVE confirmado y proximo, 390/430 y texto 130% con nombres largos. |
| H02 | RESUELTO CON PRUEBA | Defecto reproducido a scroll 0, no solo scroll residual. La especificidad anulaba el espacio del banner LOCAL + barras admin. Selector canonico compartido, sin offsets por ruta. R05/R06 y Dashboard probados al entrar y al volver a scroll 0. Cabecera no visible por scroll deliberado = NOT_RUN, no fallo. |
| H03 | RESUELTO CON PRUEBA | Campos mal conectados y contexto incompleto, no ROI incorrecta. Detalle de trazabilidad debajo. Cabeceras no parten palabras; fechas separadas; tabla desktop con desplazamiento horizontal interno para conservar columnas sin colision. |
| H04 | RESUELTO CON PRUEBA | Planes compactos y prestaciones en details accesible. 12 aperturas reales entre cuatro anchos. Precios, tiers, condiciones y checkout intactos. |
| H05 | RESUELTO CON PRUEBA | Se quita introduccion duplicada y se adelanta conexion. Una regla movil ocultaba sus acciones; excepcion local permite mostrarlas. Capturas y geometria de boton a 360/390/430. No se pulsa conectar ni nuevo codigo. |
| H06 | RESUELTO CON PRUEBA | Filtros avanzados desplegables, Cuenta compacta, CTA vacio Home en fila completa, minuto no repetido si ya aparece en estado, nivel MEDIO/ALTO/BAJO no usado como explicacion de riesgo, metodologia de picks desplegable. Datos y filtros originales preservados. |
| H07 | PENDIENTE | Una iteracion de integracion: brillo 0.90 a 1.14 y sombra mas contenida en la regla de heroes. Mismo WebP, anatomia y orientacion. No imagen nueva ni aprobacion automatica. |
| H08 | RESUELTO CON PRUEBA | Planos diagonales provenian de clip-path de body::before/after y capas atmosfericas V813/V814 heredadas. Se excluyen de ns-app y se anulan ambos clips en la capa actual. Estilos computados finales: clip none en ambos, sin transform heredado. Estados parcial/vacio conservados. La preferencia artistica del fondo sigue pendiente. |
| H09 | RESUELTO CON PRUEBA | Ajuste acotado de legibilidad: shell compartido, celdas largas de Data Marketplace y densidad KPI. No se crean analiticas, ingresos, graficas ni nueva jerarquia funcional. La semejanza artistica global de admin no se certifica en este alcance. |

### H03: datos separados de CSS

`engines/pick_grading_engine.py`, consulta `pick_grading_summary`:
la correccion anterior ya incorporada en la base recupera `p.selection` y
`COALESCE(p.pick_type,p.market)`. Antes, un payload vacio podia perder una seleccion
real guardada; ahora se recupera por el join a picks. No se revierte ese hunk.
Regresion permanente: `tests/test_temporal_context_consistency.py`, prueba de
consulta real con payload vacio y seleccion guardada.

Incremento actual de datos, cuatro lineas: se exponen `p.source`, `p.created_at`
y el `kickoff_iso` desde el instante canonico ya calculado. Asi la fila evaluada
atraviesa el contrato existente de aprendizaje; no se cambia su motor.
Si una fila cerrada aun carece de contexto, el template distingue resultado
registrado de aprendizaje pendiente, sin afirmar que no hay resultado.

Escena poblada aislada: match m-1, seleccion real de la fixture, WON, stake 1 u.,
profit 0.82 u.; `evaluable_total=1`, `decided_total=1`, ROI 82%, winrate 100%.
El template antes buscaba closed_count/graded_count inexistentes y count/picks
mensuales; ahora usa evaluable_total y by_month.total. Mes: total 1, profit 0.82.
No existe ROI mensual en ese contrato: se retira esa columna, no se fabrica.
Mes significa periodo de evaluacion; fecha de partido y fecha del pick se distinguen.
ROI usa stake evaluado; winrate usa won+lost. Las ayudas explican esos universos.
No cambian SQL de calculo, stake, liquidacion, filtros financieros, permisos ni DB real.

### QA reproducible y limites

Entorno local con DB nueva por escenario, credenciales de prueba, jobs desactivados,
red externa bloqueada y reloj de escenas focales `2026-09-07T16:00:00+02:00`.
Origen `SIMULATED_QA`, nunca REAL_PRODUCTION_OBSERVATION.

- Suite: `.venv/Scripts/python.exe .tmp_reference_review/consolidated_h01_h09/run_checks.py tests`.
  Resultado final en `pytest.xml`: 474/474 PASS, 0 fallos, 0 errores, 0 omitidos,
  267.838 s; 0 intentos de red externa. No suma ejecuciones anteriores.
- Jinja: 199 plantillas compiladas. compileall sobre Python modificado sin errores.
- Browser focal: `tools/check_consolidated_visual_review.py --label accepted_local`:
  56 vistas + 6 capturas de estres; 360x800, 390x844, 430x932, 1366x768.
  0 fallos focales, 0 errores JS, 0 overflow de pagina. El scroll interno de tabla es deliberado.
- Escenas `accepted_empty` y `accepted_partial`: 8 vistas cada una, 0 fallos.
- Navegacion final: `final_navigation/PQA-20260907200337/autonomous_product_qa_result.json`:
  10 capturas, 13 clicks reales, 9/9 journeys, 0 errores consola/JS, 0 provider calls.
- Controles negativos detectan solapamiento y circulo legacy; positivo pasa.
  No se usa un rectangulo externo de tarjeta como sustituto de las lineas de texto.
- El primer pase detecto expectativas estaticas del marcador en su antigua ubicacion.
  Sentinel y test V944 ahora exigen una unica invocacion dentro de match_header,
  sin invocacion duplicada en match_detail. No se elimina el contrato.
- Guard de privacidad/secretos en `--no-report`: 1106 archivos, 0 hallazgos confirmados
  o para revision; no imprime valores ni regenera informes historicos.
- Advertencias de pytest: acceso denegado a cache local, no fallos de tests.
- `git diff --check`: PASS (solo avisos de normalizacion LF/CRLF de Git).
- `final_manifest.json`: hashes del candidato y comprobacion byte a byte de archivos
  protegidos contra la copia local inicial; indice sin cambios preparados, HEAD intacto.
- No se mide latencia productiva, entrega Telegram, Stripe, LIVE real ni administracion real.
  Las regresiones de rendimiento/permisos/Sports Truth/Match Context pertenecen a la suite local.

### Evidencia para revision

Directorio exacto desde la raiz oficial:
`.tmp_reference_review/consolidated_h01_h09/founder_review/index.html`.

11 comparativas focales antes/despues, imagenes finales y `manifest.json`.
Los PNG originales permanecen en before/accepted_local/accepted_empty/accepted_partial.
Cada evidence.json contiene ruta, viewport, rol, escenario, reloj, huella, scroll
y geometria. Sin recorte de las capturas principales; las copias JPG solo comprimen
para facilitar lectura. Las comparaciones con el paquete historico anterior senalan
que sus escenarios pueden diferir: no se usan para certificar cambios LIVE ni metricas.
La baseline inmediata tiene reloj de ejecucion diferente; valida composicion, no frescura.

### Archivos modificados

- Datos: `engines/pick_grading_engine.py`.
- Contrato de QA: `engines/sentinel_autopilot_engine.py`.
- Presentacion: `static/app.css`, `static/v933-product.css`, `templates/base.html`,
  `calendar.html`, `membership.html`, `picks.html`, `telegram.html`, `track_record.html`,
  `match_detail.html`, componentes `v933_ui.html`, `v937_sports_lifecycle.html`, `v944_match_center.html`.
- QA: `tests/test_temporal_context_consistency.py`, `tests/test_v944_match_center_foundation.py`,
  nuevo `tests/test_consolidated_visual_review.py`, `tools/run_autonomous_product_qa.py`,
  nuevo `tools/check_consolidated_visual_review.py`.
- Documentacion: este informe. Evidencias y DB QA quedan en ubicaciones locales excluidas.

No se modifica VERSION ni se genera una release. Detener ediciones al entregar;
H07 y la aprobacion artistica del fondo quedan para revision humana.

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
