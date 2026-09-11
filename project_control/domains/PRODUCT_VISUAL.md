# Product / Visual

Calendario: [auditoria y contrato preparado](#calendario-como-hub-auditoria-2026-09-10).
Estado transversal vigente: [CURRENT_TRUTH](../CURRENT_TRUTH.md).
Las secciones previas conservan sus fechas y limites historicos.

UX-001 BLOCKED por decision humana; sin rediseno en CX-ORG-01.
Design System 1.0 y cambios visuales del candidato se conservan.

## Autoridad y cobertura

- REFERENCE_ONLY: 16 PNG oficiales segun inventario historico. No reabiertas en
  esta higiene; no nueva afirmacion MATCH ni copia de payload/instaladores.
- [Cierre visual/SE historico](../../reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md)
  conserva capturas/limites. SHARK y fondo pendientes humanos.
- SE-01: detalle fresco/stale, calendario y Directo en 1366x768/390x844,
  cinco clicks, 0 overflow/errores de consola observados; SIMULATED_QA.
- Esa muestra NO certifica todas las 199 plantillas, todo admin ni iPhone fisico.

## Hogares y preservacion

`templates/`, `static/`, contratos de contexto en app.py/engines. No moverlos,
retirar estilos por nombre Vxxx ni recalcular lifecycle en Jinja/JS.
Topbar, bottom nav, safe area y banner LOCAL SAFE se conservan.
No quitar enlaces/API como si fueran vulnerabilidad sin demostrar permisos rotos.
No reducir tiers reales ni duplicar contexto de cuenta/membresia.

## Deuda clasificada

17 archivos static tracked, 199 templates. Existencia != activos en todas las rutas.
Capas CSS historicas y selectores requieren ownership/render antes de retirada;
no se hereda el numero antiguo de 223 selectores sin medirlo de nuevo.
Los assets de marca pueden compartir contenido o nombre historico sin ser basura.
Un hash igual no autoriza borrar un contrato de ruta o una referencia oficial.

## UX-002: icono de app, 2026-09-09

APP_ICON_IDENTITY = PARTIAL: listo localmente y en PR, no desplegado.
Base c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04; commit selectivo
cdd88e507a9dd422d7e528f8eb795c2030060c3c en codex/app-icon-identity.
[PR #9](https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/pull/9).

- Maestro: `static/img/app-icons/official_app_icon_master.svg`; reutiliza el
  WebP atmosferico actual intacto, sin generar otro tiburon. No wallpaper.
- Generador offline `tools/build_app_icons.cjs`, sin instalar dependencias;
  una geometria, silueta simplificada a 16/32/48, fondo RGB opaco.
- Normal 16/32/48/64/96/128/152/167/180/192/256/512; ICO 16-256;
  maskable 192/512, escala .80 y alfa del tiburon dentro del circulo seguro.
- Fingerprint `8d0ed4207e73`, reproducible con LF/CRLF. Favicon16 658 bytes,
  favicon32 1739 bytes, PWA512 129358 bytes. No 512 para favicon.
- Manifest mantiene id/start_url/scope `/`, standalone; tema/fondo #020c18.
  Apple Touch 152/167/180, ICO real y metadatos de accesos locales actualizados.
- Rutas de iconos no inicializan negocio; cache HTTP y worker piden version
  nueva. Browser real local confirma activacion y reemplazo de worker previo,
  eliminacion de cache QA, cuatro iconos decodificados, 0 assets rotos.
- QA visual 1366x768/390x844, tamanos 16-512 y formas launcher; navegacion real
  movil Home -> Partidos y desktop Partidos -> Directo, 0 errores JS observados.
  Son representaciones: Windows/iOS/Android/macOS instalados NOT_TESTED.
  Un icono instalado puede exigir aceptar actualizacion o reinstalar segun SO.
- Iconos anteriores: brand.svg sigue ACTIVE para logo/OG, retirado del rol
  favicon/manifest; atmosphere-v2.webp ACTIVE e intacto. official.svg y
  atmosphere.svg LEGACY/REQUIRED_FALLBACK por tests/referencias. No borrados.
  shark-logo.svg ya no existia; 0 referencias de instalacion nuevas a legacy.
- 23 tests propios; 139/139 focales sobre combinacion publicable exacta.
  Suite combinada 602: 590 PASS, 12 LOCAL_SAFE_BLOCKED/NOT_CERTIFIED, 0 errors.
  Performance SHARK existente 10 lecturas: cold 93 ms, hot median 19.1 ms,
  P95 de esta muestra local 23.1 ms; 0 provider calls/render memory writes.
  Compilacion, 199 Jinja, Secret/Privacy del diff y diff-check correctos.
- CI: qa SUCCESS, preflight FAILURE, smoke FAILURE, certify-production SKIPPED.
  Preflight run 34372380601: Browser QA result missing en V944.
  Smoke run 34372380596: No module named playwright durante recoleccion.
  Ambas causas verificadas tambien en logs del SHA base c6eaa003; no son
  fallos inventados por iconos ni justifican eludir checks. CI fix separado.
- No merge/deploy, no Production Sentinel para nuevo SHA; Render workspace
  requiere confirmacion. No cambios de scheduler, CE, DB real ni Sports Truth.

Evidencia privada en `.tmp_reference_review/app_icon_20260909/`:
before.json, verification.json, staged_verification.json, XML, performance.json,
browser_evidence.json y cleanup por run. No publicar esos artefactos ni DB.

## Reconciliacion UX-002 / UX-003 / QA-002

Fecha: 2026-09-09. CREATIVE_DESIGN_DIVISION=PASS_LOCAL (formalizacion e integracion).
APP_ICON_IDENTITY=PARTIAL (implementado, no integrado ni certificado en produccion).
No significa DESIGN_MATCH, lanzamiento comercial ni aprobacion de SHARK/fondo.

### Identidad y contenido demostrado

| Etapa | Evidencia |
|---|---|
| Base preservada / main actual | c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04 |
| App Icon | cdd88e507a9dd422d7e528f8eb795c2030060c3c; padre=base; 22 rutas |
| HEAD y rama remota | 6858aedbbd04211500028b7aaf56c3f5980f833d; padre=App Icon |
| 6858aedb | mensaje `hh`; 35 rutas, SE-01, lectura/contexto/historico deportivo, higiene y documentacion |
| Origen observado | Commit externo a esta ejecucion; GitHub author login bot-NeMeSiS. No identifica por si solo a la persona/proceso que lo creo |
| Relacion | Cadena lineal, base 0 behind / 2 ahead; no cambio a assets, metadata base, generador ni tests de iconos entre cdd88e50 y 6858aedb |
| Main/PR | PR #9 OPEN, merged=false. main permanece en base. El SHA de test-merge de la PR no es un merge efectivo |
| Render actual | NOT_VERIFIED. MCP sin workspace confirmado; runtime publico no accesible por el conector usado |
| Ultima observacion productiva | c6eaa003, DAY 5, 2026-09-08; no es comprobacion nueva |

APP ICON: IMPLEMENTED=YES; COMMITTED=YES; PUSHED_BRANCH=YES;
MERGED_MAIN=NO; DEPLOYED=NOT_VERIFIED (no evidencia); PRODUCTION_CERTIFIED=NO.
PR actual contiene tambien SE/CX: requiere revisar ese contenido antes de merge.
No hubo staging, commit, push, merge, deploy ni ejecucion remota de Actions aqui.

### Division y autoridad

Fuente: [design_contracts.json](../../reference_images/design_contracts.json).
Consumidor: reference_image_manifest_engine -> autonomous_product_qa_engine ->
Founder existente. Sin nuevo engine, endpoint, scheduler o proceso.
CREATIVE_DIRECTOR, BRAND_IDENTITY_DESIGN, PRODUCT_UI_DESIGN, MOBILE_UX_DESIGN,
SPORTS_UX_DESIGN, ADMIN_DATA_UX_DESIGN y VISUAL_REGRESSION_QA son responsabilidades
de Codex y workers ya registrados; no siete empleados autonomos ejecutandose.

Las 16 PNG importadas oficiales se abrieron individualmente. Solo imagenes,
sin payload, instaladores ni codigo de REFERENCE_ONLY. Cada pantalla tiene
proposito, contenido, componentes reales, acciones, responsive, intensidad de marca,
prioridad deportiva, empty state y estado de conformidad. 16 directas + 5 derivadas.
REF-12 muestra Betis-Sevilla y tabs de Match Center, no el portal SHARK.
El manifiesto persistido ya lo reconocia; su generador tenia un override obsoleto,
ahora corregido y protegido por regresion. Ruta canonica /match/<match_id>;
/match/m-1 es el caso sintetico del runner, no una identidad productiva inventada.

FUNCTIONAL_QA y VISUAL_QA conservan estados separados de DESIGN_CONFORMANCE
(campo design_status). Una prueba funcional PASS puede coexistir con rework.
Evidencia ausente=NOT_RUN; evidencia previa necesita revision, captura, viewport
y fingerprint contractual. Automated MATCH no puede aprobar marca. Rechazo humano
prevalece. Estados: DESIGN_MATCH, MINOR_DESIGN_GAP, DESIGN_REWORK_REQUIRED,
FOUNDER_SUBJECTIVE_REVIEW. No se actualizaron baselines ni referencias aprobadas.

Brand kit: ATMOSPHERIC_SHARK, BRAND_SHARK, APP_ICON, WORDMARK, FAVICON,
PWA_ICONS y APPLE_TOUCH_ICON. Iconos/favicons/touch derivan de un solo maestro
tomado del shark atmosferico actual, intacto. Brand Shark vectorial es una fuente
independiente: compatibilidad anatomica conjunta NO certificada. Compartir azul
o tiburon no acredita BRAND_MATCH. Cero wallpapers y cero fondos del SO.

Ocho decisiones duraderas se incorporan a Product Memory existente solo durante
su escritura autorizada: anatomia, oceano, densidad, tipografia, movil, navegacion,
uso de marca y falsos PASS anteriores. Idempotencia probada en almacenamiento QA.
Consultar Founder no escribe esa memoria. Resumen compacto desplegable de siete
areas dentro de Quality existente; contratos detallados bajo disclosure.
Los gaps mostrados vienen del ledger registrado, no de una nueva auditoria global.

### Gates: historico remoto frente a repeticion local

| Gate | Historico GitHub para 6858aedb | Clasificacion / cierre local |
|---|---|---|
| qa | SUCCESS, run 34373698530 | No rerun remoto. Compilacion/Jinja/Sentinel y pruebas locales separadas |
| smoke | FAILURE, run 34373698481, job 102541012212 | CI_ENVIRONMENT_DEFECT: Playwright ausente durante collection. Workflow instala ahora requirements de browser existentes y Chromium antes de pytest; sin filtrar tests |
| preflight | FAILURE, run 34373698511, job 102541011606 | MISSING_REQUIRED_EVIDENCE: browser_qa/V944_MATCH_CENTER_FOUNDATION/browser_qa_result.json. No runner V944 conectado al job que genere las seis capturas requeridas |
| certify-production | SKIPPED | No ejecucion ni certificacion nueva |

Smoke CI fix: 3 lineas, solo workflow; cuatro regresiones (positivo y ausencia de
dependencia/browser/pytest). Segun [Playwright CI oficial](https://playwright.dev/python/docs/ci).
No dependencia nueva de produccion, no continue-on-error, no relajacion de gate.
Instalacion Ubuntu y resultado Actions posteriores: NOT_RUN, cambio aun local.
smoke_check local exit 0; warnings por dos endpoints API historicos ausentes,
no clicks ni integracion productiva certificada por ese check.

V944 reproducido localmente: contratos/Sentinel PASS, unica causa de exit 1 es
Browser QA result missing. No se clasifica como requisito obsoleto sin prueba.
No se copio un JSON historico ni se escribio PASS con seis capturas ficticias.
Para cerrar falta generacion real, aislada, vinculada al candidato en CI; el
navegador Founder de esta tarea NO sustituye la muestra Match Center V944.

Controles posteriores reintentados: V937 lifecycle PASS al reutilizar un directorio
QA heredable (antes WinError 5 por tempfile Windows); producto sin modificar.
V929 PASS tras corregir sys.path del envoltorio local, no su codigo ni expectativas.
V937 client update, V940 Calendar, Match Live Story, Continuous Sentinel static,
release identity y smoke: exit 0. V929 usa tambien matrices guardadas: no anunciar
sus 245 clicks historicos como clicks realizados ahora.
Generadores V915, Master OS, navegacion worker, Secret Guard writer, imports/routes
y link audit: LOCAL_SAFE_BLOCKED al intentar escribir evidencia fuera de QA;
pipeline checker bloqueado por proceso hijo; Madrid audit bloqueo acceso a su DB
fallback y no la abrio. Se conservan logs/limites, no PASS por omision.
V914 opcional no existe y el workflow lo omite por condicion; no es fallo del producto.
Build ZIP de CI no ejecutado localmente: no autorizacion para otro paquete de app.

### Pruebas y preservacion

- Focal Creative/iconos/workforce/Founder/CI: 95/95; regresiones negativas incluidas.
- Focal protegido SE/Sports Truth/Calendar/dashboard/performance: 131/131.
- Suite final: 623 total, 611 PASS, 12 failed XML clasificados LOCAL_SAFE_BLOCKED,
  0 errors, 0 skips. Mismos IDs que la suite previa; resultado global PARCIAL.
- Se conserva SE-01 PASS_LOCAL_SCOPE y su historico 543/555, no se reetiqueta.
- SHARK performance local: 10 lecturas, cold32.9ms, hot mediana18.8ms,
  P95 muestral27.2ms, 0 llamadas externas y 0 escrituras de memoria al render.
  No es latencia/P95 de produccion ni certificacion de toda la app.
- Founder real con sesion y DB sinteticas, desktop1366x768/mobile390x844;
  siete areas, 21 contratos, disclosures y navegacion Panel -> volver. Ocho
  interacciones contando login y back; 0 errores JS/overflow en esta muestra.
- Sin nueva comprobacion de actividad Master/CE; codigo protegido, no asumir ACTIVE.
- No providers, Telegram, Stripe, usuarios reales ni memoria operativa modificados.
- Evidencia, capturas, hashes, compilacion/Jinja/privacidad y resultados exactos:
  `.tmp_reference_review/creative_design_20260909/verification.json`, XML,
  `browser_final.json`, `founder-final-desktop.png`, `founder-final-mobile.png`,
  `performance.json` y `gate_*`. Directorio privado ignorado/excluido del release.
- HEAD/indice y DAY3/4/5 se verifican por hash; no limpieza legacy ni retiros funcionales.
- Verificador final: 4147 archivos previos intactos; 9 existentes modificados
  deliberadamente y 3 nuevos. app.py y assets de icono intactos; 199 Jinja,
  compileall, privacidad/Secret Guard del diff (12 archivos, 0 hallazgos), diff-check PASS.
- Retirada QA por manifiesto tras finalizar procesos: 28 directorios propios
  procesados; 1 temporal V937 retenido por acceso denegado. Se conserva la evidencia
  y no se reparan ACLs ni se llama a esto una limpieza completa. Este limite nuevo
  no reescribe el resultado historico CLEANUP_FINAL_ERRORS=0 de SE-01.

### Decision y siguiente accion

Formalizacion Creative cerrada LOCAL_ONLY. Reconciliacion global PARTIAL: gates
CI y despliegue no cerrados, marca sin aprobacion. Ninguna regresion nueva de
producto demostrada; el cero no es certificacion exhaustiva de produccion.
SAFE_TO_CONTINUE_CX_ORG_01_R2=NO y SAFE_TO_START_RESULTS_01=NO en este cierre.
1. Generar evidencia V944 real en el job aislado y verificar smoke en CI, via PR/checks.
2. Revisar alcance de PR #9 ampliado por 6858aedb antes de cualquier merge.
3. Confirmar workspace Render para leer el despliegue efectivo y certificarlo despues.
No se inicia ninguna de esas fases automaticamente. Gasto nuevo iniciado=0;
facturacion total del sistema no auditada. Secretos expuestos=0.

## Calendario como hub: auditoria 2026-09-10

Alcance: dependencias y preparacion documental solicitadas, no implementacion de
RESULTS-01 ni rediseno global. HEAD `92a4f04348cf64c8567c70afe3981a9f791ec29d`,
rama `codex/app-icon-identity`, indice vacio. Candidato previo conservado.
No nueva lectura de GitHub/Render ni certificacion productiva en esta auditoria.

### Rutas y dependencias

| Ruta | Clasificacion | Implementacion/dependencia observada; decision |
|---|---|---|
| `/calendar` | CANONICAL | `calendar_page` -> `v932_safe_dashboard_data(compact=True)` -> `v940_calendar_context` -> `calendar.html`; destino de navegacion, formularios y Home |
| `/partidos` | COMPATIBILITY_ALIAS | Mismo handler/template. Referencias en SHARK assistant/context, fallback live, QA y Sentinel; conservar |
| `/calendario` | COMPATIBILITY_ALIAS | Mismo handler real; tambien aparece en V896_ROUTE_ALIASES. Registro V897 respeta rutas existentes y NO lo reemplaza por redirect |
| `/calendario-global`, `/partidos/calendario` | COMPATIBILITY_ALIAS | Mismo handler/template. Las cinco rutas comparten contrato en prueba local; conservar |
| `/partidos-hoy` | LEGACY | Handler real `match_hub_page`, no `calendar_page`. Su entrada V896 no sustituye la ruta existente. No confundir mapping declarado con redirect efectivo |
| `/match-hub`, `/resultados` | LEGACY | `match_hub_page` -> `dashboard_data` -> `match_hub.html`; `/resultados` usa lane=results por defecto. Auditorias/client maps aun las mencionan; no borrar ni crear otra pantalla |
| `/sports-hub` | EXTERNAL_DEPENDENCY | Handler separado `sports_hub_page`, template propio. Codigo Telegram genera app_url hacia esta ruta; SHARK/admin tambien enlazan. Dependencia saliente configurada, no prueba de mensajes enviados |
| `/sports`, `/today` | COMPATIBILITY_ALIAS | Aliases del hub separado anterior, NO de Calendar. Preservar hasta migracion y comprobacion de consumidores |
| `/api/calendar` | CANONICAL | API de la misma proyeccion V940; validada solo en test local con snapshot sintetico. No endpoint nuevo ni consulta productiva |

Anclas de codigo: `app.py` calendar_page, match_hub_page, sports_hub_page,
register_alias_if_missing, api_calendar y auto_job payload daily_matches.
Dependencias: `templates/components/v933_navigation.html`,
`templates/partials/client_flow_bar.html`, `templates/home.html`,
`templates/client_app_center.html`, `engines/shark_context_presentation_engine.py`,
`engines/shark_ai_product_assistant_engine.py`, `engines/live_match_experience_engine.py`,
`engines/navigation_integrity_engine.py`, `engines/sentinel_autopilot_engine.py`.
Favoritos externos/bookmarks/enlaces ya enviados: NOT_OBSERVED; ausencia de hits
internos no probaria cero dependencias externas. Ninguna ruta retirada/redirigida.

### Soporte real frente al objetivo

BACKEND_ALREADY_SUPPORTED significa codigo conectado y limites descritos, no
cobertura completa de datos reales ni certificacion end-to-end en produccion.

| Capacidad | Estado y limite demostrado |
|---|---|
| Seleccionar fecha | BACKEND_ALREADY_SUPPORTED: `date=YYYY-MM-DD` con lane=today/tomorrow filtra match_date normalizado Madrid dentro del snapshot disponible; no consulta historica ilimitada |
| Hoy / manana | BACKEND_ALREADY_SUPPORTED: tabs y siete chips desde hoy. Fecha fuera de esos siete se agrega si llega por URL |
| Ayer / flechas / date picker visible | DESIGN_READY: no controles equivalentes expuestos actualmente; input date es hidden. Consulta historica completa y navegacion combinada REQUIRES_RESULTS_01 |
| Todos por fecha | BACKEND_ALREADY_SUPPORTED dentro del snapshot para lane=today con date; no existe un lane=all reconocido. No rotular como catalogo completo ilimitado |
| En directo | BACKEND_ALREADY_SUPPORTED: lane=live selecciona valid_live_events y vuelve a exigir status_info canonico is_live; no filtra por fecha seleccionada |
| Proximos | BACKEND_ALREADY_SUPPORTED: lane=upcoming selecciona valid_upcoming_matches, sin restriccion de fecha. No tab principal actual; un filtro por fecha compuesto REQUIRES_RESULTS_01 |
| Finalizados | BACKEND_ALREADY_SUPPORTED: lane=finished/results selecciona finished_matches, sin restringir a date. Tab actual conserva date en URL, pero no aplica esa interseccion; REQUIRES_RESULTS_01 |
| Favoritos | BACKEND_ALREADY_SUPPORTED: favoritos de sesion (partido/equipo/liga), coleccion disponible, no interseccion con date. Combinacion cronologica REQUIRES_RESULTS_01 |
| Con pick | BACKEND_ALREADY_SUPPORTED: lane=with_pick/picks sobre snapshot; with_pick=1 tambien filtra una coleccion por fecha. Relacion por match_id y valid_active_picks, no historial de todos los picks |
| Busqueda/capas | BACKEND_ALREADY_SUPPORTED: q/league/team/country/status/sort/with_pick. league y status son coincidencias textuales, no enums/IDs exactos; no prometer un selector de estados canonicos por esos parametros |
| Agrupacion | BACKEND_ALREADY_SUPPORTED: dia -> canonical_competition_surface_contract.group_key, canonical_id y country. Regresiones Primera/Segunda correctas. Facetas/contador de ligas siguen basados en nombre |
| Orden/paginacion | Dias ordenados; ligas por relevancia y filas reordenadas por sports_relevance_sort_tuple dentro del grupo. No paginacion V940 ni garantia de orden puramente horario por sort=time; REQUIRES_RESULTS_01 |
| Match Center | BACKEND_ALREADY_SUPPORTED: macro match_card y detalle canonico. No detalle alternativo para historicos |
| Volver al contexto | Parcial: JS sessionStorage por URL y back_forward, caducidad 2 h. Boton propio de Match Center apunta a `/calendar` sin date/filtros. Retorno completo y prueba browser REQUIRES_RESULTS_01 |
| Home -> catalogo | BACKEND_ALREADY_SUPPORTED: enlaces `/calendar` y accesos lane=today, sin otra pagina nueva. Contexto explicito de otra fecha requiere preservar parametros; no inventar fecha desde contador |

Cadena observada: tabla matches -> lector SELECT query_only -> resumen deportivo
compartido/cache -> proyeccion V940 -> grupos -> macro match_card -> Match Center.
El resumen lee hasta 800 matches (orden preferente updated_at/kickoff_iso/fecha)
y 300 picks; date no se aplica en SQL de ese resumen. Campos esenciales ausentes
pueden excluir un partido. Por ello una fecha vacia NO demuestra que no exista
historial almacenado. `calendar_experience_data` es una implementacion anterior,
sin llamada encontrada desde estas rutas: sus tabs/limites no prueban soporte V940.
No se modifica TTL, Sports Truth, fuentes, persistencia ni ranking en esta tarea.
Track Record sigue `v742_track_record_context`/pick_grading_results/picks: nunca
usar ese historico financiero como archivo general de resultados deportivos.

### Diseno preparado, no interfaz implementada

DESIGN_READY aqui = contrato documental, no DESIGN_MATCH ni browser QA.
REF-08 y REF-10 reabiertas fisicamente en esta auditoria: Home curado frente a
agenda por dia/competicion, filas compactas desktop, adaptacion movil especifica.
REF-10 es MATCHES/Calendar; REF-12 sigue Match Center with SHARK analysis.
No se reabrieron las otras 14 en esta tarea ni se atribuye nueva conformidad.

- Home decide que merece atencion; Calendar responde que se juega en una fecha.
  Deportes/favoritos/LIVE confirmado/relevancia primero, SHARK y picks despues.
- Un solo destino principal, nombre conceptual Calendario. Desktop mantiene
  densidad y acceso a Historico/Telegram/Cuenta segun referencia, no cinco botones
  impuestos a todas las anchuras. No cambio de labels aplicado todavia.
- Propuesta historica sustituida por decision expresa del Founder el 2026-09-10:
  Inicio, Calendario, Directo, Picks, Cuenta. REF-08/REF-10 y el shell muestran
  Cuenta como quinta accion; SHARK conserva accesos contextuales. Sin sesion,
  Entrar conserva el acceso. No anadir sexta accion ni sustituir Cuenta.
- Franja cronologica compacta: anterior, Ayer, Hoy, Manana, selector, siguiente;
  Madrid Time existente. Filtros separados de fechas, combinables solo tras
  verificar backend. No botones ficticios ni badges de estado inventados.
- Grupo: logo autorizado o fallback intencional, nombre/ID canonicos y pais
  cuando proceda. Ahora el header renderiza icono futbol generico, no logo de liga;
  los datos de pais/ID del grupo no equivalen a presentacion ya completada.
- Fila: equipos/escudos proporcionados; hora protagonista si upcoming, score y
  minuto confirmado si LIVE, score final verificado si final; suspendido/aplazado
  explicitos. Ausencia nunca 0-0. Usar macro y contratos actuales, no otro lifecycle.
- En desktop, grupos horizontales compactos; en movil, identidad/score/fecha
  antes de acciones secundarias. No tarjetas gigantes ni paneles anidados extra.
- Volver: URL interna validada con fecha/capas y restauracion de scroll razonable,
  con fallback seguro a Calendar. No aceptar destinos externos ni crear otro detalle.

### Validacion y continuidad

10/10 tests focales existentes, 0 failures/errors/skips, entorno QA aislado:
cinco aliases con handler/template reales y snapshot doblado; pagina/API coherentes;
5/500 entidades sinteticas, busqueda, filtros reversibles, macro/JS estaticos y
agrupacion/identidad canonica. No tests debilitados ni datos demo en producto.
Tres escrituras fuera de la frontera QA bloqueadas; cero conexiones externas
exitosas registradas. No accesos a DB productiva. El primer launcher python no
estaba disponible y el runtime general carecia de werkzeug: no llegaron a pytest;
la ejecucion final uso `.venv/Scripts/python.exe` existente, sin instalar paquetes.

Evidencia privada ignorada: `.tmp_reference_review/calendar_hub_audit_20260910/`
(`before.json`, copias documentales previas, `focal.xml`, `last_execution.json`).
No navegador nuevo, prueba nativa PWA ni suite global repetida por cambios solo
documentales. Los tests con dobles no certifican historial real, retorno/scroll
real ni screenshots. Suite global previa sigue PARTIAL, no reetiquetada.

RESULTS-01 permanece BLOCKED en CX-003. Reutilizara la base demostrada; pendientes:
seleccion historica suficiente/independiente de LIVE TTL, fecha x filtros,
orden/paginacion, controles de fecha y retorno con contexto. No repetir agrupacion
ni construir catalogo/detalle/Track Record paralelos. APP ICON/CI sigue su gate
separado, sin avance de publicacion por esta auditoria. Sin cambios de producto,
staging, commit, push, PR, merge o deploy; candidato y DAY 3/4/5 preservados.

## CX-DESIGN-02: comparacion y correccion local, 2026-09-10

Estado: **PARTIAL**. Esta iteracion sucede a la auditoria aceptada; no la repite.
No RESULTS-01, DATA-01, nueva ruta, worker, sistema visual, limpieza ni publicacion.
HEAD `92a4f04348cf64c8567c70afe3981a9f791ec29d`, rama `codex/app-icon-identity`.
Indice vacio y sin cambios. El diff previo sigue preservado en `before.json` y
copias selectivas, dentro de evidencia privada ignorada. No es otra release.

### Cambios demostrados

- Calendar: el `details.v940-calendar-advanced` envolvia la raiz y ocultaba
  cabecera/resumen cuando estaba cerrado. Ahora envuelve solo el formulario;
  encabezado y coleccion siempre quedan fuera. Handler y cuatro aliases intactos.
- Navegacion: etiqueta Calendario en enlaces existentes; Cuenta sigue quinta
  accion autenticada. Destinos y permisos sin cambios. Home conserva SHARK
  contextual; acceso al track record rotulado Historico de picks.
- Fecha: reduccion de copy ocultaba `.v937-card-trust`, que contiene `time` junto
  a un badge tecnico. Se oculta solo `.v937-confidence-badge`; fecha recuperada
  en Home, Live y Calendar. Ninguna conversion horaria nueva.
- Tokens: escudos 24/32/48/72, logos de liga 20/28/40, score 28/20, nombre 14,
  fecha/competicion 12 px. Las tres dimensiones `!important` del propietario
  `.v933-team-logo` neutralizan reglas `.crest` V827/V828/V829 medidas a 30-34px;
  no se retiro compatibilidad ni se anadio otra hoja. `object-fit: contain` intacto.
- Jerarquia: Calendar desktop 78px por fila en muestra, score 20px/escudo32;
  Home/Live score28/escudo48. Una unica tarjeta importante Home deja de ocupar
  un tercio estrecho. Date/score siguen viniendo del contrato canonico.
- Fatiga de bordes: propietarios de signals/empty states prevalecen sobre
  selectores legacy por subcadena `state/empty`. No se borro CSS historico global.
- Match: atmosfera limitada a 46%/540px, opacidad .32, derecha2%/arriba15%; movil
  conserva comportamiento existente. No se regenero ni sustituyo ningun asset.
- Entidades movil: acciones con espacio para palabras completas y metricas en
  dos columnas. La ultima accion de Player ya no fragmenta "competicion".
- Cache-busting de las dos hojas afectadas: `design-02-sports-1`. No VERSION bump.
- Design Memory guarda nav, Calendar hub, Home seleccionado, track record de
  picks, SHARK contextual y tokens deportivos. Mantiene siete responsabilidades,
  cero procesos nuevos y los tres ejes de QA independientes.

El saludo previo se conserva byte a byte en helper/test/Home/app.py: 77 pruebas
de franjas, CET/CEST, DST y nombre seguro pasan. Client dashboard consume el mismo
helper. Sin email/username como saludo ni logica horaria duplicada en Jinja.

### Comparacion fisica y limites

Las 16 PNG se abrieron individualmente, incluyendo las siete admin. REF-12 sigue
MATCH_CENTER_WITH_SHARK_ANALYSIS. No se le reasigno una pantalla SHARK independiente.
Capturas reales LOCAL/SIMULATED_QA, no produccion. Se compararon 15 superficies
en 1366x768 y 390x844: 10 correspondencias directas y 5 derivadas (sin PNG propia).
Galeria privada: `.tmp_reference_review/design_02_iteration_20260910/comparisons.html`.

| Superficie | Referencia | FUNCTIONAL_QA local | VISUAL_QA observado / pendiente |
|---|---|---|---|
| Home | REF-08 directa | PASS rutas/cards/saludo | Fecha visible y score legible; primer viewport y duplicacion de partido entre bloques pendientes |
| Calendar | REF-10 directa | PASS estructura/aliases/click | Fila compacta; controles duplicados, bordes y espacio antes del primer partido aun excesivos |
| Live | REF-09 directa | PASS fresh/stale | Score/minuto reales; muestra de un LIVE no certifica densidad multiparty |
| Match | REF-12 directa | PASS fresco/stale/final/unknown | Escudos y atmosfera contenidos; paneles/copy y muchos vacios siguen lejos de referencia |
| Picks | REF-11 directa | PASS lectura/acciones existentes | Estado vacio inspeccionado; variante poblada NO_OBSERVADA |
| Account | REF-15 directa | PASS lectura/nav Cuenta | Jerarquia accesible; geometria/branding no aprobados; logout no reejecutado como nuevo gate |
| Team | REF-12 derivada | PASS render/fecha | Botones y metricas movil mejorados; cabecera y paneles sin datos excesivos |
| Player | REF-12 derivada | PASS render/ID QA/fecha | Boton corregido; sin foto inventada; densidad pendiente |
| Competition | REF-10 derivada | PASS render/ID4335/fecha | Separacion de identidad preservada; sin logo oficial en muestra; cabecera excesiva |
| Track Record | REF-13 directa | PASS lectura | Estado vacio, no inventa ROI; variante poblada NO_OBSERVADA |
| Memberships | REF-14 directa | PASS lectura | Catalogo existente, sin checkout probado ni precios/tier modificados |
| Telegram | REF-16 directa | PASS lectura QA | Codigo solo QA; conexion/envios reales NOT_RUN |
| SHARK | REF-12 analisis derivado | PASS lectura limitada | Acceso contextual existente; estado generico por falta de picks/evidencia, no analisis ficticio |
| Admin dashboard | REF-01 directa | PASS sesion QA real/lectura | Rail y datos; no auditoria de todas las herramientas operativas |
| Founder | REF-01 derivada | PASS sesion QA real/lectura | Tablas con scroll interno; composicion movil derivada, no referencia propia |

DESIGN_CONFORMANCE de esas 15 superficies: DESIGN_MATCH=0, MINOR_DESIGN_GAP=0,
DESIGN_REWORK_REQUIRED=15. Incluye dependencia de marca/fondo global no resuelta;
no significa 15 regresiones funcionales ni 15 nuevas incidencias independientes.
Siete tipos de MAJOR_GAP identificados: anatomia conjunta de marca, atmosfera,
Home primer viewport, Calendar controles/densidad, Match paneles/copy, entidades
cabeceras/vacios, SHARK composicion generica. Ninguno pasa por hash/asset existente.
BRAND_ANATOMY=REWORK_REQUIRED/NOT_CERTIFIED: icono raster, logo vectorial y
referencias difieren en silueta/tratamiento. BACKGROUND=DESIGN_REWORK_REQUIRED:
la distribucion de luz y textura actual no reproduce la profundidad de las PNG.
La decision subjetiva del Founder sigue pendiente, pero no sustituye estos gaps.

League logos: tokens preparados, header actual con icono generico; no logo nuevo
inventado ni descarga. Escudos de prueba usan fallbacks; tamanos/aspect ratio
verificados, nitidez/identidad de todos los escudos reales NOT_CERTIFIED.
Admin REF-02 a REF-07 abiertos pero sus rutas no recorridas nuevamente en esta
iteracion. No confundir imagen inspeccionada con pantalla de producto certificada.

### Browser y QA reproducible

Servidor real local con sesiones de cliente/admin QA, DB temporal, jobs apagados,
secretos externos vacios, CSP local y guardas de red/escritura/procesos. No perfiles
personales ni copia de DB productiva. El escenario deportivo es SIMULATED_QA con
reloj Madrid fijo 2026-09-10T06:50:49.282770+02:00. No evidencia de LIVE real DAY 3-7.

- Matriz: nueve superficies x ocho viewports = 72 observaciones DOM: 1440x900,
  1366x768, 1024x768, 834x1194, 430x932, 390x844, 375x812, 360x800.
  Cero overflow horizontal/cards, imagenes rotas y fechas ocultas en esa matriz.
  No equivale a detector exhaustivo de colisiones ni a DESIGN_MATCH.
- 20/20 clicks nav (cinco destinos x desktop/tablet/390/360). Ademas apertura y
  cierre de filtros, tarjeta -> Match -> Calendar. Regreso a /calendar funciona;
  conservacion de parametros sigue REQUIRES_RESULTS_01, no se certifica.
- Lecturas reales de HTML: fresh LIVE 67/0-0 aparece; stale excluido de Home,
  Calendar y Live, detalle dice Actualizacion pendiente y ultimo marcador conocido;
  final2-0 no LIVE; unknown VS, no cero inventado. Cuatro entidades QA, no proveedor.
- Captura prematura Founder movil detecto overflow transitorio; inspeccion estable
  posterior: scrollWidth375 < viewport390, tabla con scroll propio. Recapturada.
  Iconos de fuente tambien recapturados tras carga estable; no se oculto el registro
  inicial en observations.json. Cero errores JS de pagina consultados; no 4xx/5xx
  en traza del servidor final. No son tasas de produccion.
- Focal final: **296/296**, 0 failures/errors/skips, 20.412s. Incluye 19 regresiones
  nuevas de presentacion, 77 saludo, 29 Sports Truth, 63 Calendar, 28 SE evidence,
  10 reutilizacion/permisos/diagnostico, 6 temporal, 6 identidad, 23 iconos, 35 V944.
- Focal tras corregir expectativas: 82/82. Suite final **754: 742 PASS + 12 failed
  XML LOCAL_SAFE_BLOCKED/NOT_CERTIFIED; 0 errors, 0 skips; 193.749s**. PARTIAL global.
  IDs bloqueados comparados con greeting/full_final.xml: diferencia vacia.
- Dos expectativas sustituidas con evidencia: workforce exigia ocultar el padre
  temporal; ahora exige ocultar solo badge y preservar padre. Memoria exigia ocho
  decisiones; ahora igualdad completa con contrato vigente, IDs unicos y las seis
  decisiones nuevas. No se rebajo ninguna guarda ni se modifico un test deportivo.
- Los 12 NOT_CERTIFIED: un Playwright WinError5 antes de Chromium; cinco launches
  bloqueados por QA_PROCESS_BLOCKED; un intento de quitar PID fuera de QA bloqueado;
  cinco pruebas de endpoints cron/evolution interceptadas por LOCAL SAFE 403 antes
  del contrato interno. No continue-on-error, skips artificiales ni bypass.
- Compilacion de app/engines/workforce/tools/tests PASS; Jinja 199/199; diff-check
  PASS (solo advertencias LF/CRLF). Secret/Privacy V938 --no-report: 1120 archivos,
  0 hallazgos confirmados/revision/privacidad. No se regeneraron informes canonicos.
- 80 intentos bloqueados en suite global, 3 focal, 0 conexiones externas exitosas.
  Browser final sin intentos externos registrados. Login/codigo Telegram afectan
  solo DB QA; no se afirma cero mutaciones dentro del entorno de prueba.
- Performance: contratos locales de reutilizacion por peticion y aislamiento
  intactos. Ocho CSS activos suman 226672 bytes gzip local (221.36 KiB), +489 bytes;
  sin nuevos raster/video. Presupuesto CSS historico sigue WARNING; no latencia ni
  P95 de produccion medidos en esta tarea.

Comandos principales desde la raiz con `.venv/Scripts/python.exe -B`:
`.../run_qa.py --seed-schema tests --junitxml=.../full-final.xml --tb=short`;
focal: diez modulos enumerados en focal-final.xml. Compilacion con pycache_prefix
privado y `-m compileall -q app.py engines automation_workforce tools tests`.
Guard: `tools/check_repository_privacy_and_secrets.py --no-report`.
Wrapper privado reutiliza guardas SE; no inicia otro worker. XML, fuentes del arnes,
hashes, capturas, observaciones, clicks y traza HTTP estan en la misma carpeta ignorada.

### APP ICON y continuidad

GitHub main consultado por conector read-only: c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04.
PR #9 OPEN/merged=false; rama remota y local 92a4f043; ancestry c6eaa003 -> cdd88e50
-> 6858aedb -> 92a4f043. Ningun merge/deploy realizado. Render actual NOT_VERIFIED;
no se confunde la rama con produccion. APP_ICON=PARTIAL.
23 tests de assets/manifest/fingerprint pasan localmente. Instalacion nativa iOS,
Android, Windows/macOS, actualizacion de launcher y PWA reopen siguen NOT_TESTED.
No se promete actualizacion silenciosa por versionar URLs.
Gates remotos observados siguen smoke SUCCESS, qa/preflight FAILURE; fix Secret
Guard del runner V944 sigue LOCAL_ONLY. Intento V944 local de esta iteracion:
WinError5 al iniciar driver, cero capturas V944 validas. MISSING_REQUIRED_EVIDENCE /
LOCAL_SAFE_BLOCKED; estas capturas CUA no se presentaron como paquete V944.

SE-01=PASS_LOCAL_SCOPE preservado; suite global nunca PASS. DAY3/4/5 y codigo
Sports Truth/Madrid/cron/Continuous Evolution sin nuevas ediciones. app.py y
helper/test de saludo coinciden con huella anterior. Client dashboard solo suma
dos cambios de copy a su diff previo; sin alteracion de datos ni ROI.
SAFE_TO_PUBLISH=NO. SAFE_TO_CONTINUE_DESIGN=YES. SAFE_TO_START_RESULTS_01=NO.
Siguiente iteracion: cerrar evidencia APP ICON en runner permitido, corregir los
gaps visuales objetivos ya capturados y repetir solo consumidores afectados.
Este cierre no inicia esa iteracion ni RESULTS-01. Sin staging/commit/push/merge/deploy.
