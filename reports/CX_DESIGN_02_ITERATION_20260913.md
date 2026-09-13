# CX-DESIGN-02: iteracion local de conformidad

## Decision

**PARTIAL / IN_PROGRESS / LOCAL_ONLY. SAFE_TO_PUBLISH = NO.**
No PR, push, merge, deploy, nueva limpieza ni nuevo macrotrabajo.
Base main: `c4a81003de1b5ccdb3036831583e9c1eb65e4417`.
HEAD documental Design: `2c1a9b676036ae2630e14028cd5539fe1713acf4`.
Candidato preservado: `7202c1886aec7fee03267b1a709313804360592a` (23 rutas).
El arbol de trabajo, no un nuevo SHA publicado, contiene esta iteracion.

Las 16 PNG oficiales se abrieron fisicamente antes de editar. No se sustituyeron
ni se utilizaron sus equipos, resultados o estadisticas como datos reales.
REF-12 sigue siendo MATCH_CENTER_WITH_SHARK_ANALYSIS.
Las capturas usan handlers Flask reales y Chromium, con fixtures existentes en DB
temporal y reloj explicito. Son SIMULATED_QA; no certifican proveedores/produccion.
El Player ID de QA no se presenta como identidad real autorizada.

## Revision individual del candidato

Las cinco rutas de Project Control no se copiaron del candidato. Su continuidad
procede del commit documental autorizado. Las 18 restantes se revisaron por diff:

| Ruta | Decision | Motivo/limite |
|---|---|---|
| app.py | ADAPT_TO_CURRENT_MAIN | Helper de saludo; preservar main y hotfix; correcciones funcionales acotadas |
| engines/madrid_time_engine.py | KEEP | Una funcion Madrid con nombre seguro, sin logica horaria en templates |
| reference_images/design_contracts.json | ADAPT_TO_CURRENT_MAIN | Memoria de diseno y anatomia no aprobada automaticamente |
| static/v933-product.css | ADAPT_TO_CURRENT_MAIN | Editar reglas canonicas; densidad, estado temporal y tamanos |
| static/v933_design_tokens.css | KEEP | Tokens deportivos reutilizables |
| templates/base.html | ADAPT_TO_CURRENT_MAIN | Fingerprints CSS y marca compacta; iconos web intactos |
| templates/calendar.html | ADAPT_TO_CURRENT_MAIN | Corregir disclosure y presentar fecha sin nuevo backend |
| templates/client_app_center.html | ADAPT_TO_CURRENT_MAIN | Seleccion Home; no rotular manana como HOY |
| templates/components/v933_navigation.html | ADAPT_TO_CURRENT_MAIN | Cuenta quinta accion; Calendar y aliases activos |
| templates/home.html | KEEP | Saludo canonico; posterior import con contexto de sesion |
| templates/match_detail.html | ADAPT_TO_CURRENT_MAIN | Datos disponibles abiertos, cobertura pendiente compacta |
| templates/partials/brand_logo.html | ADAPT_TO_CURRENT_MAIN | Usar el icono aprobado, no otra silueta legacy |
| templates/team_detail.html | ADAPT_TO_CURRENT_MAIN | Forma sin muestra no es cero; colecciones por estado |
| tests/test_autonomous_product_qa_workforce.py | ADAPT_TO_CURRENT_MAIN | Contrato temporal y marca activa actual, no referencia legacy |
| tests/test_creative_design_division.py | ADAPT_TO_CURRENT_MAIN | Roles existentes, ejes independientes, Support derivado y gaps reales |
| tests/test_design02_calendar_presentation.py | ADAPT_TO_CURRENT_MAIN | Aliases, fecha, disclosure, cero real y score ausente |
| tests/test_design02_reference_conformance.py | ADAPT_TO_CURRENT_MAIN | Home/Team/Match, disponibilidad y favoritos |
| tests/test_madrid_greeting.py | KEEP | Limites, DST, nombres y escape |

KEEP significa conservar la propuesta revisada, no certificacion visual ni copia
byte-identica de toda la ruta. Ningun cherry-pick global ni restauracion de main.

## Correcciones demostradas

| ID | Causa | Resultado |
|---|---|---|
| D02-F01 | Disclosure exterior de Calendar ocultaba la cabecera/coleccion | Disclosure limitado al formulario avanzado; aliases preservados |
| D02-F02 | Home recuperaba toda la coleccion al faltar partidos de hoy | Seleccion por disponibilidad y etiqueta PROXIMOS correcta |
| D02-F03 | Team separaba por fecha, incluyendo FT de hoy en proximos | Colecciones disjuntas por estado canonico; cinco negativos reproducidos antes |
| D02-F04 | ID de actividad determinista con precision de un segundo; conexion abierta tras INSERT fallido | ID efimero unico y cierre finally; error no ocultado; Account repetible |
| D02-F05 | Siete imports Jinja sin contexto hacian desaparecer favoritos | Import con contexto; alta/baja y persistencia tras reload comprobadas |
| D02-F06 | Soporte marcaba sent antes de registrar solo el asunto; no guardaba el mensaje | Sin confirmacion falsa; POST 503 sin registrar contenido como entregado; formulario deshabilitado |
| D02-F07 | No existe canal de persistencia/entrega de Soporte | **OPEN_FUNCTIONAL_P1 / BACKEND_DEFECT / REQUIRES_SEPARATE_WORK_ITEM**; no se crea infraestructura ni se afirma entrega |
| D02-F08 | La accion Calendario en Team apuntaba al hub legacy distinto | Enlace a /calendar con filtro team; /match-hub y sus dependencias conservados |
| D02-V01 | Regla movil heredada apilaba cinco metricas de forma | Cinco columnas estables; sin cambiar calculos |
| D02-V02 | Formulario de Soporte con grids anidados estrechaba el mensaje | Fieldset unico, asunto/mensaje a ancho completo |

No se cambia la expectativa de un test para ocultar un error. La expectativa de
texto tutorial antiguo de Soporte queda sustituida por indisponibilidad explicita,
manteniendo categorias de privacidad/cancelacion y marcador de trazabilidad.
Tres pruebas negativas demuestran que las tres rutas no pueden fingir entrega.

## Calendar: frontera de producto

BACKEND_ALREADY_SUPPORTED: los cinco aliases comparten handler/plantilla, coleccion
snapshot, parametro date, busqueda y filtros actuales; favoritos y Match Center.
Ayer/Hoy/Manana, flechas y selector generan enlaces al contrato existente; no se
agregan consultas, almacenamiento historico, lifecycle ni llamadas de proveedor.
Se conservan filtros en los enlaces/formulario de fecha. Las franjas del saludo
son 05/12/20 Europe/Madrid, no hora del dispositivo ni UTC directo.

REQUIRES_RESULTS_01: archivo historico completo, cobertura de finales persistidos,
intersecciones fecha/estado completas, paginacion y retorno avanzado con contexto.
Los tabs actuales no equivalen a TODOS los resultados deportivos historicos.
Track Record sigue siendo exclusivamente historial de PICKS.

## Matriz de superficies

Baseline y recaptura: 1440x900, 1366x768, 1024x768, 430x932, 390x844, 375x812,
360x800. Son 147 combinaciones de 21 superficies. Admin movil es derivado, no
una referencia movil inexistente. La matriz privada registra ruta, template real,
captura, geometria y acciones. Se inspeccionan pares desktop/movil y paneles admin.

`PASS lectura` certifica solo el recorrido/estado local indicado, no todas las
operaciones externas de esa pantalla. Visual QA geometrica y conformance son ejes
distintos; cero overflow no prueba semejanza. No hay DESIGN_MATCH certificado.

| Pantalla | Referencia | FUNCTIONAL_QA local | VISUAL / DESIGN_CONFORMANCE | Gap principal |
|---|---|---|---|---|
| Home /app | REF-08 | PASS seleccion/saludo/enlaces | DESIGN_REWORK_REQUIRED | Anatomia, atmosfera y composicion frente a referencia |
| Calendar + aliases | REF-10 | PASS fecha/favoritos/filtros actuales | DESIGN_REWORK_REQUIRED | Logos oficiales y densidad frente a referencia |
| Directo | REF-09 | PASS empty; LIVE poblado no certificado | DESIGN_REWORK_REQUIRED | Falta comparacion poblada con LIVE autorizado |
| Match Center | REF-12 | PASS detalle/navegacion en fixture | DESIGN_REWORK_REQUIRED | Jerarquia y cobertura parcial de modulos |
| Team | DERIVED REF-12 | PASS estado, resultados, enlaces | DESIGN_REWORK_REQUIRED | Densidad, vacios repetidos y texto tecnico residual |
| Player | DERIVED REF-12 | BLOCKED ID real ausente | NOT_TESTED | Fixture no equivale a jugador real |
| Competition | DERIVED REF-10 | PASS lectura/enlaces | DESIGN_REWORK_REQUIRED | Presentacion de identidad/logos y datos parciales |
| Picks | REF-11 | PASS empty; apuesta real NOT_RUN | DESIGN_REWORK_REQUIRED | Estado poblado no certificado |
| SHARK | DERIVED REF-12 | PASS acceso; proveedor NOT_RUN | DESIGN_REWORK_REQUIRED | Integracion de marca y analisis real no certificado |
| Track Record | REF-13 | PASS estado sin metricas ficticias | MINOR_DESIGN_GAP | Comparacion con historial evaluable pendiente |
| Memberships | REF-14 | PASS lectura; cobro NOT_RUN | MINOR_DESIGN_GAP | Acciones comerciales no certificadas |
| Account | REF-15 | PASS enlaces/logout/repeticion | MINOR_DESIGN_GAP | Jerarquia y acciones de cuenta no exhaustivas |
| Telegram | REF-16 | PASS lectura; envio/vinculacion real NOT_RUN | MINOR_DESIGN_GAP | Estado conectado real no certificado |
| Support | DERIVED REF-15 | BLOCKED canal real | MINOR_DESIGN_GAP | Disponibilidad honesta, no entrega funcional |
| Admin Dashboard | REF-01 | PASS lectura/navegacion | DESIGN_REWORK_REQUIRED | Densidad, rail y primer viewport |
| Admin Telegram | REF-02 | PASS lectura; envios NOT_RUN | DESIGN_REWORK_REQUIRED | Composicion operativa/estados reales |
| Admin Payments | REF-03 | PASS lectura; Stripe NOT_RUN | DESIGN_REWORK_REQUIRED | Composicion y acciones comerciales |
| Admin Automation | REF-04 | PASS lectura; ejecuciones NOT_RUN | DESIGN_REWORK_REQUIRED | Jerarquia operativa |
| Admin Data | REF-05 | PASS lectura; providers NOT_RUN | DESIGN_REWORK_REQUIRED | Densidad y cobertura de datos |
| Admin Launch | REF-06 | PASS lectura; acciones externas NOT_RUN | DESIGN_REWORK_REQUIRED | Composicion y controles operativos |
| Admin Picks | REF-07 | PASS lectura; publicacion NOT_RUN | DESIGN_REWORK_REQUIRED | Estado poblado y densidad |
| Founder | DERIVED REF-01 | PASS lectura/roles/ejes | DESIGN_REWORK_REQUIRED | Longitud excesiva, resumen compacto pendiente |

Conteo: DESIGN_MATCH 0; MINOR_DESIGN_GAP 5; DESIGN_REWORK_REQUIRED 16;
Player NOT_TESTED 1. MAJOR_DESIGN_GAP > 0 en pantallas criticas.
No se transfiere al Founder la correccion objetiva de estos gaps.

## Marca y activos

Icono maestro, favicon, Apple Touch, PWA 192/512 y maskable no se redisenan.
Topbar/rail/acciones compactas reutilizan el derivado de 96px aprobado; no usan
la imagen de 512px para el favicon. Los activos legacy conservados no se borran.
BRAND_SHARK y ATMOSPHERIC_SHARK se declaran DESIGN_REWORK_REQUIRED frente a las PNG:
mandibula, cabeza y silueta difieren. Misma fuente no significa BRAND_MATCH.
Se solicita aclaracion de autoridad sobre cambiar o conservar la anatomia del
icono aprobado; no se modifica ese icono sin resolver la contradiccion.
Native device install/update NOT_TESTED; no nueva certificacion productiva.

## QA y evidencia

Baseline propio: 690 = 647 PASS + 43 FAIL clasificados por aislamiento, 0 errors.
Primera integracion: 803 = 760 PASS + los mismos 43 FAIL, 0 errors.
Ronda posterior: 837 = 793 PASS + 44 FAIL, 0 errors; un fallo adicional era la
expectativa de texto antiguo de Soporte, explicado arriba y corregido en contrato.
Verificacion final: **837 = 794 PASS + los mismos 43 bloqueos de baseline, 0 errors**.
Nuevos IDs fallidos respecto a baseline: 0. Focal final independiente: **292/292 PASS**.
El ajuste posterior de CSS de Soporte se verifica con focal y siete recapturas.
El ultimo cambio de enlace Team -> Calendar tiene 60/60 pruebas relacionadas PASS,
incluida una regresion nueva. La suite completa de 837 precede esos ajustes finales;
no se afirma que la nueva prueba formara parte de esa ejecucion completa.
Compilacion: 961 Python, 0 errores; py_compile PASS; Jinja: 199 templates, 0 errores.
Secret/Privacy Guard: 0 hallazgos; scanner y politica intactos. diff-check PASS.
Main limpio e indice Design vacio; 53/53 huellas protegidas de main y 26/26 copias
de preservacion correctas, incluidas las 23 rutas originales del candidato.

Los 43 bloqueos no son PASS: 31 fronteras de ubicacion de DB local, cinco rutas
operativas bloqueadas por LOCAL_SAFE, seis subprocess bloqueados y una escritura
fuera del directorio temporal autorizado. Los mismos IDs fallaban en el baseline.
Se conservan los XML y una clasificacion individual privada. Los 12 historicos
siguen siendo una evidencia separada NOT_CERTIFIED, no se sustituyen por esta cifra.

Recorridos completos: 466 comprobaciones; 464 PASS y dos falsos fallos del arnes
en Soporte por contar tambien el banner LOCAL SAFE como role=status. Selector
acotado a Soporte; retest intermedio 138/138 PASS. Tras el enlace canonico de Team,
**retest final 140/140 PASS**, incluye fecha, favoritos,
Account/logout, estado no disponible de Soporte y las rutas afectadas. El banner
LOCAL SAFE se conserva. La politica de red no cambia.
Team -> /calendar?team=... obtiene HTTP 200 y cabecera visible mediante clic/tap
real a 1366x768 y 390x844; no se elimina ni modifica el handler /match-hub.
Ronda anterior: cinco fallos reales Account/alerts y bloqueos SQLite secundarios;
corregidos mediante D02-F04, no ocultados por el runner.

Escudos: siete escenarios (valido, 404, red bloqueada, abort, vacio, ausente,
URL malformada) por desktop/movil. Cero imagen rota visible y cero imagen+fallback
simultaneos en las rondas realizadas. Valido = asset neutral QA, no escudo oficial
de proveedor ni validacion de CDN. Las URLs externas siguen bloqueadas.

Matriz final deduplicada: 21 superficies / 147 combinaciones. Cero errores HTTP,
JS, imagenes rotas, cabeceras ocultas u overflow horizontal observados. Cero
clipping visible en el detector; los siete h1 sr-only de Match Center son
accesibilidad intencional, no texto visible pisado. No es certificacion exhaustiva
de toda colision posible ni de todos los estados/datos del producto.
35 recapturas adicionales sustituyen observaciones de Calendar/Team/Support/Founder,
sin sumar dos veces una misma combinacion de pantalla y viewport.

Performance: test de single-flight P0 PASS; diez lecturas locales SHARK 200,
db-cache-only, mediana caliente 72.5 ms y p95 observado 107.5 ms. Todas fueron hit:
cache fria NOT_CERTIFIED en esta medicion; no es un benchmark productivo global.
Preview LOCAL SAFE operativo, solo loopback, DB aislada, red externa/Render/Stripe/
Telegram OFF. El launcher privado permite entrar sin publicar la credencial efimera.

Artefactos privados: baseline/, after/, final/, polish/, actions-*.json,
crests-*.json, execution.json, result.xml, technical-verification-final.json,
iteration-evidence.json. No incluir DB, credenciales, logs ni capturas masivas en PR.

## Proteccion y siguiente paso

SE-01 PASS_LOCAL_SCOPE, 12 LOCAL_SAFE_BLOCKED historicos NOT_CERTIFIED.
DAY 3/4/5, App Icon, crest fallback y objetos/copia del candidato preservados.
Sports Truth, Competition Identity, Madrid Time y agregados se comprueban con
pruebas locales; no se reinterpreta esa QA como Production Sentinel.
Ningun cambio en main, DB productiva, usuarios reales, membresias reales, Stripe,
Telegram comercial, providers, Cron, Master Scheduler o Continuous Evolution.

Continuar exclusivamente CX-DESIGN-02 desde esta matriz y las decisiones abiertas.
Antes de PR faltan conformidad critica y cobertura funcional. No se declara
OPEN_FUNCTIONAL_P1=0 ni que todas las acciones visibles esten certificadas.
No iniciar RESULTS-01, DATA-01 ni CX-ORG-01 R2.
