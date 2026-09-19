# Continuidad local - 2026-09-19

ESTADO: PARTIAL / VALIDADO LOCAL EN ALCANCE / NO PUBLICADO.

## Cierre actual: preview utilizable + FINAL_OVERRIDES_STALE_LIVE_V1

Ordenes recibidas: `51b3a305-6632-4472-a93e-8a2a918d3384/Texto pegado.txt`
y el incremento acotado `d6cc3af3-924b-4cd9-a204-359b7e4897be/Texto pegado.txt`.
Mismo worktree Sentinel y HEAD c4a81003. Sin staging/commit/publicacion.
Design y main no editados; main limpio y HEAD/main/origin/main locales iguales.

### Preview reproducible

- Doble clic: `tools/local_review/start_nemesis_preview.bat`.
- Parada controlada: `tools/local_review/stop_nemesis_preview.bat`.
- URL cliente `http://127.0.0.1:54910/app`, Calendario `/calendar`,
  Sentinel `/admin/sentinel-issues` (Panel local > Admin).
- Instancia REAL en marcha al cierre, loopback, SQLite QA y secretos externos
  ausentes. No se instala nada. Reutiliza el Python ya preparado; si desaparece,
  informa del limite, no instala ni busca indiscriminadamente.
- Inicio, segundo inicio sin duplicar, parada y reinicio probados. Puerto 54910
  ocupado por socket QA: usa 54911 sin detenerlo. Tras liberarlo, vuelve a 54910.
- Bloqueo de proceso propio y nonce de instancia; la parada espera al ejecutor,
  no mata otros procesos ni elimina la DB o los resultados. No nueva cola.

### Replay puntual, no certificacion productiva

FINAL_OVERRIDES_STALE_LIVE_V1 = PASS_LOCAL / REAL_WORLD_REPLAY_QA.
Final 5-0, equipos, fecha, competicion y kickoff proceden del encargo del fundador;
no verificados aqui contra un proveedor. T1/T2, sus minutos y metadatos de
cobertura son observaciones ilustrativas del replay, no reconstruccion historica.
DB separada y temporal; no se inyecta este partido en la preview habitual.

- Antes, reproduccion: 2 FAIL en `candidate-2b5b879db77a4c4d904e23d1d2063343`.
  El upsert reemplazaba FINAL por LIVE antiguo; la proyeccion no exponia la
  procedencia independiente persistida. En navegador se demostro ademas que el
  resumen contaba el final pero su array realtime lo omitia, dejando 1-0 visible.
- Ahora: comparacion temporal y escritura atomicas; observaciones antiguas,
  iguales o de fecha desconocida no revierten el FINAL. Correccion final mas
  reciente permitida. Rollback/cierre de conexion en error. Invalida cache al commit.
- El array realtime incluye finales para que lleguen a consumidores abiertos.
  Se conservan timestamps independientes desde raw_json, sin migracion ni inferir
  cobertura a partir del lifecycle. Events PARTIAL; stats STALE; lineups probables
  no se elevan a confirmadas. El motor Sports Truth protegido no fue editado.
- 10/10 tests, incluidos sockets Flask y navegador reales a 1366/390, DB real QA,
  T1 -> T2 -> T3 -> T2 antiguo, concurrencia, relojes invalidos e iguales.
  Directo 1-0/36' -> 5-0/FINAL en el mismo nodo sin recarga. Home, Live,
  Calendar, Partidos y Match Center coinciden al siguiente render.
- Evidencia final: `data/local_dev/candidate-98bcacc65f3b41879d5c4589be7cda08/`
  (`result.xml`, `temp/test_real_flask_browser_final_0` y `_1`, PNG/JSON).
  La suite de ese directorio tiene un fallo de arnes descrito debajo; los diez
  casos replay pasan. Evidencia focal anterior: `candidate-d4189d4674c846b3bb8b1386de6764fd`.
- Produccion, API-Football, feed sostenible, alineaciones, Player IDs, eventos/
  stats completos, highlights y derechos: NOT_CERTIFIED por este caso.

### Rendimiento y visible

Mismo dataset 603, SHA256 `69102dd46c36c1b804fe72a851a9fffc9e6318abb0f5bc7a495f757e4b84fc05`.
Timeline por lote acotado a la peticion /app, 20 entradas por partido; no nueva
cache global de usuarios. Prueba mantiene contenido, aislamiento y copias.
Perfilado instrumental: SQL frio 1719 -> 1210; caliente 317 -> 153.
La memoizacion experimental de identidades no mejoro y se retiro solo ese cambio.
Los informes de experimentos se conservan; no son el resultado final de latencia.

A/B final serial sin cProfile, misma revision y bytes del dataset:
- Baseline sin prefetch: 5.730 / 2.084 / 2.095 s.
  `app-profile-before-ef924fce7a9e467abb2ed8e6efe57f0a/result.json`.
- Con prefetch: 5.737 / 2.085 / 2.040 s.
  `app-profile-after-413fc6518a114b16bd92a2821867fc63/result.json`.
Latencia practicamente equivalente: NO se declara timeout resuelto ni mejora
global significativa. Coste restante: normalizacion/verdad deportiva repetida,
identidades y agregacion de contexto. P50/P95 productivos INSUFFICIENT_SAMPLE.

Recomendaciones: agrupar titulo + evidencia elimina la celda vacia de 78px.
Calendario: section interna en vez de main anidado; composicion conservada.
No CSS global, cambios de icono/tiburon/fondo ni aprobacion artistica nueva.

### QA de esta revision

- 380 casos distintos comprobados en seleccion pertinente, NO suite global.
  Primer pase: 379 PASS + 1 FAIL de arnes (Windows spawn reimportaba el runner
  e iniciaba otra suite). Sin ocultarlo ni omitir el caso: main guard corregido.
  Bloque Sentinel completo: 22/22 PASS en `candidate-aad4817674414960849740044174ca8e`.
  Los otros 358 PASS conservan el mismo codigo de producto. No sumar repeticiones.
- 45/45 vistas finales: 15 rutas x 1366/390/430, Flask/SQLite/browser reales;
  Home -> detalle -> retorno -> Calendario y selector ES por formulario/CSRF.
  `data/local_dev/preview-review-9692fa8c6fc842128581b481282fa669/result.json`.
  Cero errores JS, overflow horizontal, shell fallido o solicitudes externas.
  La pasada anterior tenia seis fallos por main anidado, corregidos, no ignorados.
- 203 Jinja, compilacion, diff-check PASS. Secret/Privacy: 1174 archivos,
  cero secretos confirmados, pendientes o identificadores por revisar.
- Los 12 LOCAL_SAFE_BLOCKED y 43 ambientales historicos siguen NOT_CERTIFIED;
  esta seleccion no los transforma en PASS. No afirmar todos los botones probados.

### Huella y reanudacion

Huella fuentes/pruebas/herramientas: `8e3475faa56656546f4a9535163ca1ed48722afc3e3371df0d27abc128197326`.
Manifest acumulado `data/local_dev/final-source-manifest.json`: 129 rutas,
72 PRODUCT / 33 TEST / 14 TOOL / 10 DOCUMENTATION; indice vacio.
Delta propio desde huella 20c69f5e: 16 fuentes/pruebas/herramientas:
app.py; realtime_state_engine.py; v934_realtime_sports_engine.py;
calendar.html; recommendations.html; test_final_replay.py; test_home_request_work.py;
test_local_preview_launcher.py; check_local_candidate.py; run_sentinel_local.py;
local_review/check_preview.py; preview.py; run_preview.bat;
start_nemesis_preview.bat; stop_nemesis_preview.bat; profile_local_app.py.
Siete documentos operativos existentes actualizados, sin otra cola.
Blobs/copias anteriores, R8, contratos, App Icon, fallback y DAY 3/4/5 conservados.
Ediciones congeladas tras este cierre. Proximo paso: revision humana de esta
preview y diff; luego autorizacion/gates de integracion, sin ejecutarlos aqui.
Reanudar leyendo esta seccion y verificando solo delta contra manifest; no repetir
inventarios, suites historicas ni activar otro frente automaticamente.

## Continuacion A-E desde Sentinel aceptado - cierre anterior 2026-09-19

Autorizacion: encargo recibido `5937778a-eca4-474f-8488-b5461a513e61/Texto pegado.txt`.
Se ejecutan las fases independientes sobre el candidato completo existente.
Sentinel queda aceptado y su fuente no se modifica en esta continuacion. Los
cierres inferiores son historia con su propia revision; no se suman sus pruebas.

### Revision, alcance propio y preservacion

- Worktree: `C:/Users/aloha/.codex/worktrees/nemesis-sentinel-operaciones`.
- Rama `codex/sentinel-operaciones-local`, HEAD/base
  `c4a81003de1b5ccdb3036831583e9c1eb65e4417`; sin commit ni staging.
- Huella de fuentes, pruebas y herramientas (documentacion excluida):
  `20c69f5e602f7d9c6c706446bea5c3aa7b045d75cb2fbe026aa2a7c591d28bb9`.
- Manifest acumulado: `data/local_dev/final-source-manifest.json` y copia
  `final-source-manifest-20c69f5e602f7d9c.json`. 122 rutas modificadas/nuevas:
  72 PRODUCT, 31 TEST, 9 TOOL, 10 DOCUMENTATION. No son 122 cambios de esta fase.
  El manifest anterior se conserva antes de sustituir la vista latest. Sus
  etiquetas R8/PR14 indican coincidencia de ruta historica, no equivalencia de hunks.
- Esta fase interviene 22 rutas de fuente/pruebas/herramientas, ademas de actualizar
  siete documentos ya existentes. El resto del candidato previo se conserva:
  `app.py`; `engines/match_context_engine.py`, `realtime_state_engine.py`,
  `realtime_surface_adapter.py`, `v934_realtime_sports_engine.py`;
  `localization/ui.json`; `static/v934-realtime.js`;
  `templates/admin_autonomous_picks.html`, `admin_betting_center.html`,
  `admin_recommendations.html`, `betting_recommendations.html`,
  `components/betting_evidence.html`, `opportunities.html`, `recommendations.html`;
  `tests/test_directo_realtime_http.py`, `test_home_request_work.py`,
  `test_local_betting_evidence.py`, `test_local_client_continuity.py`,
  `test_local_membership_preservation.py`;
  `tools/check_local_close.py`, `check_local_journeys.py`, `profile_local_app.py`.
- Main limpio y HEAD/main/origin/main locales iguales a c4a81003 en la comprobacion
  final. No nueva consulta remota ni runtime productivo. Design no editado/importado;
  R8 conservado, R9 NOT_CERTIFIED. Candidato 7202c188, iconos, crest fallback,
  contratos deportivos y DAY 3/4/5 preservados. No nuevas ramas/worktrees ni retiradas.
- PR14 ef759cb8 se compara mediante objeto local y comportamiento ya adaptado;
  no merge ni reaplicacion completa. Parche deportivo unificado no disponible:
  no se afirma verificacion de sus bytes ni se busca indiscriminadamente.

### A. Directo y Match Center

Corregidos periodos observados ET/P (prorroga/penaltis), finales PEN/AET y
descuento 45+3/90+7 en el detalle; minuto 0 sigue valido. Fuente observada
preservada antes de la normalizacion del lifecycle. Catalogo ES/EN/FR unico.
P es penaltis en curso; PEN es final confirmado, segun el contrato existente.
No hay conversion missing->0-0, kickoff->LIVE, desaparicion->FT o score->GOAL.

Regresion inicial: 6 FAIL/2 PASS en
`data/local_dev/candidate-bc93afd1302b40a5b5a6d59187549b96/result.xml`.
Cierre focal 11 PASS en `candidate-5dd59f4a0f10458b8e7bb52af7fb8e18/result.xml`,
repetido despues dentro de la seleccion final. Flask/socket/SQLite y Chromium
reales, sin interceptar respuestas de app. ES desktop, EN 390, FR 430;
actualizacion con pagina abierta, mismo nodo/enlace/foco/query, retorno,
STALE y FT. Match Center comprobado al abrir/recargar, no se promete polling propio.
Capturas: `data/local_dev/directo-operational-close/`.
Fuente deportiva SIMULATED_QA persistida; proveedor, cuota y cobertura NO certificados.

### B. Rendimiento /app y aislamiento

Dataset acotado reproducible: 603 partidos QA, seis ligas y siete dias.
Instrumentacion de fases de Home, ranking, relevancia, normalizacion, colecciones,
get_picks y formas SQL saneadas. Forma SQL repetida no demuestra mismos parametros.

- Antes: `data/local_dev/app-profile-before-dfa8d69ac0e64cae88c4b78cc052bf08/result.json`.
  Frio 21.781 s; calientes 7.631/8.775 s; SQL 2593/825/825.
- Despues, ejecucion serial del arbol final:
  `data/local_dev/app-profile-after-20d6a7d5897d40498401564f51401867/result.json`.
  Frio 19.496 s; calientes 6.174/6.411 s; SQL 1728/317/317; boundary events 0.
- Prueba adicional sin cProfile: 5.763/2.128/2.069 s, directorio
  `app-profile-after-4fd1d54467a24889896b84d87833ae19`. No comparacion antes/despues
  equivalente; SQL 0 en ese modo significa NO INSTRUMENTADO, no ausencia de SQL.
- La ejecucion `app-profile-after-de70c2158ce445c288f14014e47644c7` coincidio con
  suite/navegador y dio 41.394/16.933/16.600 s. Se conserva como muestra con
  contencion, excluida de la comparacion serial; no se oculta ni acredita regresion productiva.

Reutilizacion solo por request /app GET/HEAD con claves DB/usuario/rol/plan/idioma/dia;
datos mutables aislados, sin aumentar TTL. Reutilizacion de normalizacion pura y
eliminacion de pertenencia N-cuadrado. No se cachea fallback dependiente del estado
actual. La copia de hub completo ensayada resulto costosa y se retiro antes del cierre.
El cache persistente de match_hub antes compartia favoritos entre usuarios: ahora
su clave incluye identidad/rol/plan/favoritos y no escribe hub de usuario a estado global.

Regresiones antes: `candidate-c2426f520b2e423da750005df4355fca/result.xml`
(4 FAIL/2 PASS), y aislamiento `candidate-5d2671d328204edea1bcce83b6aef522/result.xml`.
Once pruebas focales actuales pasan: equivalencia funcional, DB/usuario/request,
no mutacion compartida, rutas/metodos excluidos y fallback con estado cambiado.
No aumento de timeout. La carga fria sigue lenta; no se reproduce ni resuelve
el timeout historico de produccion. P50/P95 productivos INSUFFICIENT_SAMPLE.

### C. R8 y recorridos visuales

R8 ya integrado selectivamente se conserva. REF-08 reabierta y comparada con
capturas actuales; no nueva anatomia, icono, fondo ni capa CSS. H07/arte sigue
pendiente y R9 no obtiene certificacion. No se fabrica DESIGN_MATCH.

La primera matriz real detecto /historico 500 en ES/EN/FR: el alias legacy
invocaba una escritura diagnostica bloqueada por LOCAL SAFE. Ahora /historico
es alias directo del handler canonico de Track Record, antes del registro legacy.
La regresion HTTP fuerza fallo de escritura y comprueba 200/template canonico;
no se relaja la proteccion. Matriz anterior conservada:
`data/local_dev/journeys-1d3e82bac0794936bd54a019ff758209/result.json`.

### D. SHARK y apuestas con evidencia

Se corrige el consumidor activo v565: prioridad de liga y cercania de cuota ya
no generan confianza/riesgo/seleccion supuestos. El resultado separa HECHOS,
CONTEXTO, ANALISIS y BETTING; WAIT para proximo elegible, NO_BET para no elegible.
Sin modelo/vigencia acreditados: confidence, score, risk y seleccion recomendada
ausentes, nunca cero sustitutivo. Picks editoriales existentes no se reescriben.

Precios observados finitos >1, outcome identificado por nombre canonico exacto,
fuente/bookmaker/timestamp solo cuando constan; no asignar el outcome de otro
equipo. odds_updated_at no se sustituye por updated_at generico. JSON inesperado,
NaN e infinito rechazados. Componente comun ES/EN/FR y enlace natural al partido.
SHARK expresa insuficiencia sin inventar narrativa ni prometer beneficio.

Convertir WAIT a pick devuelve 409 sin escritura. GET del endpoint mutante
devuelve 405; POST conserva admin/CSRF y exige evidencia publicable. El enlace GET
roto y los botones admin sin operacion real se sustituyen por revision acotada
de consulta y enlace editorial existente. No comandos arbitrarios ni servicios nuevos.
Regresiones antes: seis fallos en
`data/local_dev/candidate-c95a6eaa4b044e5793c7dafcf158f000/result.xml`;
once pruebas nuevas pasan con 61 de i18n (72 PASS) en
`candidate-64ecc4f896a349eb82937522b3c41988/result.xml` y en cierre transversal.
No se certifican todos los motores legacy, narrativas historicas ni modelo de apuestas.

La inspeccion final detecto contador sobredimensionado y recuadros anidados
en /recommendations. Se sustituyen por encabezado/lista y tarjetas canonicas,
sin nueva CSS ni cambios de arte. Primera revision movil ahora y239.7 a 390 px,
con el enlace al partido visible. No implica conformidad global ni elimina
todos los espacios mejorables del sistema visual. Las capturas anteriores se conservan.

### E. Cliente, admin y membresias

Regresion real: expiracion generica podia degradar rol ADMIN aunque tuviera un
plan PRO/ELITE vencido. La consulta ahora excluye ADMIN por rol; expiracion de
clientes normales sigue FREE. Antes un fallo en
`data/local_dev/candidate-afc9e568dcbb408cbaae10ae38ff98d4/result.xml`.
Trece casos actuales de membresia: grant manual/paid, suscripcion vigente,
cancelacion, expiracion, ADMIN y gating FREE/PRO/ELITE. ELITE+ no se inventa.
Stripe permanece LOCAL SAFE; ningun usuario, pago ni DB real modificados.

Navegador real registra usuario QA, logout/login por password, favoritos
persistentes, filtros/selector fecha y recorrido de partido. Soporte llega a
SQLite y bandeja admin; no se afirma email ni respuesta humana. Recuperacion,
Telegram y pagos externos siguen NOT_TESTED; no se accionan para llenar evidencia.

### QA exacto final y revision visible

- Seleccion transversal final tras ajuste visual: **584 PASS,
  0 FAIL, 0 ERROR, 0 SKIP**, 179.087 s. XML:
  `data/local_dev/candidate-27a8935d392744f8bef51d15acc4ab22/result.xml`.
  La ejecucion anterior de 588 en `candidate-10600de50cf34fa9a189ef44b5a9c4bf`
  repetia cuatro casos de test_shark_intelligence_platform al incluir el modulo
  dos veces. Comparados los conjuntos classname/nombre: ningun caso ausente en
  el cierre de 584. No se suman duplicados como nueva cobertura.
  Incluye Sentinel existente, HTTP/browser deportivo, Madrid/i18n, soporte,
  nuevas regresiones de rendimiento/aislamiento/apuestas/alias/membresia.
  No toda la suite global. Los 43 ambientales y doce positivos historicos
  permanecen NOT_CERTIFIED; no se usaron skips para convertirlos en verde.
- Browser final: `data/local_dev/journeys-3984a95a874f44c495f3b6d9dc4de961/result.json`.
  57 aperturas de rutas cliente (19 por idioma), 96 vistas/capturas cliente/admin,
  1366 desktop y 390/430 mobile. Siete recorridos de acciones: Home/Calendar/Match/Back
  ES/EN/FR, selector fecha, favoritos add/reload/remove, admin/users y
  logout/registro FREE/logout/password login; soporte persistente comprobado aparte.
  Fallos, errores JS y requests externas detectados: 0. No se certifica cada control
  de cada modulo ni efectos externos. Datos marcados QA, no evidencia productiva.
- Tras compactar /recommendations, nueve capturas y nueve recorridos
  revision -> partido -> retorno adicionales (ES/EN/FR x 1366/390/430), cero
  overflow/errores JS/red externa:
  `data/local_dev/betting-review-final-e89986d35e6a45c7bf3aecd181c9c41f/result.json`.
  Para esa pantalla usar `review-es-1366.png` y `review-es-390.png` de este
  directorio, no la captura anterior de la matriz. Focal 11 PASS antes de la
  seleccion transversal final: `candidate-cfd9c172e47f4514a33585451bab09b5/result.xml`.
- Lectura HTTP/estructura de Project Control: 26 PASS tras consolidacion documental,
  `data/local_dev/candidate-24b1e36220254dcdb53d33cbffd32f53/result.xml`;
  incluidos de nuevo en los 584, no se suman como cobertura independiente.
- 203 Jinja y compilacion PASS. Secret/Privacy: 1170 archivos, cero hallazgos
  confirmados, a revisar o de privacidad (20:20:23 Madrid). Diff-check PASS; staged 0.
- Evidencia visual vigente: `home-es-1366.png`, `calendar-es-390.png`,
  `match-es-390.png`, `admin-recommendations-390.png` en el directorio journeys.
  Revision de apuestas cliente actual en betting-review-final, segun el punto anterior.
- Preview LOCAL SAFE con app real: `http://127.0.0.1:54910`; /api/health 200.
  Abrir /app -> /calendar -> partido -> retorno, /recommendations y paneles admin.
  Acceso QA efimero solo en metadata local, nunca en este informe. /health no es
  ruta valida; su error diagnostico previo no se presenta como health PASS.

### Bloqueos, consolidacion y parada

SAFE_TO_PUBLISH = NO. Arte/anatomia H07 y conformidad global pendientes; frio
/app aun costoso; provider/cobertura/minutos reales/derechos/cuotas y ciclo
comercial externos requieren autorizacion/evidencia. ELITE+ indefinido.
No afirmar cero defectos globales por 584 pruebas o por ausencia de overflow.

Design y candidato visual siguen PRESERVE; sus diferencias utiles no autorizan
retirar la rama. PR14 es dependencia deportiva parcialmente adaptada, no absorbible
en bloque; PR12/parche unificado siguen separados. El worktree documental conserva
trabajo unico. Ninguna rama/worktree se declara retirable por este cierre.

Sin staging/commit/push/PR/merge/deploy, cambios en main/Render/cron/tareas,
secretos/proveedores/DB real/usuarios/membresias/pagos o envios Telegram.
No reescritura de Sentinel, inventario global, limpieza ni nueva cola.
Ediciones de producto congeladas en la huella indicada. Proximo paso minimo:
revisar candidato y capturas, despues decidir integracion y autorizaciones
externas por ambito. Reanudar desde manifest, no repetir el preflight historico.

## Continuacion funcional tras organizacion - 2026-09-19

El cierre de organizacion inferior se conserva como evidencia anterior, no como
certificacion del arbol nuevo. No se reclasificaron UNKNOWN/duplicados, no se
regeneraron inventarios y no se reescribieron la cola ni Conversation Index.

### Capacidad visible y defectos corregidos

- Sentinel reutiliza el registro SQLite y Product Experience Worker existentes.
  Antes, recargar una seleccion historica podia sustituirla por el ultimo job.
  Ahora `?job=<id>` conserva el trabajo solicitado en recarga, enlace y segunda
  pestana; un ID inaccesible nunca se sustituye silenciosamente por otro.
  Las respuestas antiguas de consultas no pisan una seleccion posterior.
- El panel muestra el recorrido confirmado QUEUED/RUNNING/COMPLETED desde los
  timestamps persistidos en Madrid, sin porcentajes ni exito supuesto. Permanece
  separado del estado de incidencias y de cualquier publicacion.
- Directo: las filas con final confirmado tambien reciben la proyeccion canonica
  existente. Se prueba partido -> detalle -> retorno -> marcador observado nuevo
  con pagina abierta -> caducidad STALE -> FT confirmado -> detalle final.
  Los datos son SIMULATED_QA en SQLite; el transporte y Flask son reales. No se
  consume proveedor ni se certifican cobertura, cuota, derechos o LIVE productivo.
- Match Center: el minuto observado 0 ya no desaparece en normalizacion, adaptador
  web o plantilla. Ausente no se convierte en 0 y FT/STALE no conservan minuto LIVE.
  Contexto ausente queda en un desplegable compacto, manteniendo visibles datos
  conocidos. No se inventan estadio, arbitro, pais ni resultados.
- SHARK/contexto: se localizan EN/FR las dos variantes heredadas del aviso de
  evidencia insuficiente y el rotulo "Partido en curso", en el catalogo existente.
  No se traducen identidades oficiales ni se altera la evidencia deportiva.

### Revision y diff propio

Base/HEAD: `c4a81003de1b5ccdb3036831583e9c1eb65e4417`, rama
`codex/sentinel-operaciones-local`. Se conservan los 108 paths locales del cierre
anterior. Este incremento afecta ocho rutas de producto/pruebas y este informe:

- `static/sentinel-operations.js`: seleccion durable, respuestas obsoletas y recorrido confirmado.
- `tests/test_sentinel_operational_browser.py`: nuevo recorrido Flask/socket/SQLite/Chromium.
- `app.py`: proyeccion de filas finales y preservacion del minuto 0 observado.
- `engines/sports_domain_model_engine.py`: no perder 0 al elegir la fuente de minuto.
- `templates/components/v944_match_center.html`: minuto 0 y contexto ausente compacto.
- `localization/ui.json`: mensajes EN/FR concretos detectados en capturas.
- `tests/test_directo_realtime_http.py`: recorridos deportivos reales por HTTP local.
- `tests/test_local_integrated_surfaces.py`: regresiones positivas y negativas correspondientes.

Son cambios sobre el candidato acumulado, no se atribuye a esta sesion todo el
diff contra main. Estado final: 110 rutas modificadas/nuevas, indice vacio;
main sigue limpio en c4a81003. Huella de estas ocho fuentes, NO del arbol completo:
`d7ddf2b62e1efcd1c147057e2db36a3be5ceb7b581eec2025771dbd2fdfacb81`.
Detalle por archivo: `data/local_dev/sentinel-operational-close/increment-source.json`.

### Demostracion y QA congelada

- 547 PASS, 0 FAIL, 0 ERROR, 0 SKIP; 163.452 s. Seleccion transversal final:
  `data/local_dev/functional-frozen-10343e8da8154a189862241332ebd39b/result.xml`.
  Incluye Sentinel HTTP/navegador, Directo, Match Center, contratos deportivos,
  Madrid/i18n, R8, soporte, SHARK, membresias y lectura de Project Control.
  No es toda la suite global; no se suman ejecuciones solapadas ni se convierten
  los 43 bloqueos ambientales historicos en PASS.
- Los 13 casos focales del registro y concurrencia siguen separados:
  `data/local_dev/sentinel-core-close.xml`. Incluyen procesos concurrentes,
  reclamacion atomica, recuperacion INTERRUPTED y ausencia de reintento automatico.
- Navegador operacional: doble clic y ocho solicitudes simultaneas recuperan un
  job, un intento y una reclamacion. GET no solicita; ID ajeno, visitante,
  FREE/PRO/ELITE, CSRF, accion y parametros indebidos se rechazan. Error inyectado
  despues del proceso hijo real queda FAILED saneado, sin retry. Es una prueba
  negativa QA, no un fallo observado en produccion. Evidencia:
  `data/local_dev/sentinel-operational-close/result.json`.
- Vista previa final: `http://127.0.0.1:54910/admin/sentinel-issues`.
  Job visible `17390f5ff1ae4e088ebe76c2774f8c78`, COMPLETED, intento 1;
  revision del alcance del worker
  `41552bfcf8cb4d7966ccabe9107783db2fa27992355f25b8e9cabcc26b78de3d`.
  Resultado: 8/8 plantillas presentes, 0 hallazgos en el alcance estatico.
  Ese resultado NO certifica recorridos, ausencia global de defectos ni produccion.
- Al reiniciar realmente el supervisor local, el job previo
  `58b1887461ae4bf3840af0d321f57ce5` conservo sus 15 campos sin cambios,
  COMPLETED/intento 1. Almacenamiento QA: `data/local_dev/sentinel_jobs.sqlite`;
  app de demostracion: `data/local_dev/sentinel_preview.sqlite`, nunca DB real.
- Browser final 1366/390/430, texto 200% a 430, busqueda/foco conservados,
  0 errores JS y 0 requests externas: `data/local_dev/sentinel-browser/result.json`.
  Capturas legibles del job y evidencia: `sentinel-job-1366.png`,
  `sentinel-job-390.png`, `sentinel-evidence-390.png` en ese mismo directorio.
- Directo/Match Center: ES 1366, EN 390, FR 430, reloj navegador New York,
  hora deportiva Madrid; socket HTTP real, sin interceptar respuestas de la app.
  Capturas y resultados: `data/local_dev/directo-operational-close/`.
- 202 Jinja y compilacion: PASS. Los fallos intermedios de minuto cero y copia
  dinamica se reprodujeron y cerraron; los XML previos se conservan, no se ocultan.
  Una invocacion de pruebas fue bloqueada por TMP fuera del area QA; se corrigio
  la ruta sin rebajar la frontera. Una sonda inicial uso /health inexistente y
  activo el bloqueo de escritura del registro 404 en LOCAL SAFE; no se modifico
  esa proteccion. La ruta real /api/health devuelve 200. La ruta inexistente no
  se presenta como comprobacion aprobada.
- Secret/Privacy Guard final: PASS, 1165 archivos, 0 hallazgos, sin imprimir
  valores sensibles (19:15:49 Europe/Madrid). Diff-check PASS, staged 0.

### Limites y reanudacion minima

Main y Design no se editan; R8 conservado, R9 no certificado. Iconos, fondo,
anatomia, DAY 3/4/5 y certificacion deportiva preservados. Sin staging, commit,
push, PR, merge, deploy, llamadas deportivas ni pagos/envios reales.

Sentinel queda VALIDADO LOCAL en este recorrido. Su ejecutor es la revision
estatica acotada ya disponible, no una plataforma de reparacion/despliegue.
Directo se actualiza con pagina abierta; Match Center se comprobo al abrir y
recargar, no se afirma actualizacion continua propia. El timeout productivo de
/app del 15/09 sigue sin reproducirse/certificarse. R8 y membresias locales se
revalidan, pero arte H07, datos reales, integracion de candidatos separados y
pagos/webhooks externos siguen pendientes con sus limites anteriores.

Ediciones congeladas tras este cierre. Proximo paso minimo: abrir el job final,
revisar su evidencia y el diff incremental, antes de autorizar integracion o
pruebas externas concretas. No repetir organizacion ni activar el siguiente
frente automaticamente desde este informe.

## Cierre incremental de organizacion - 2026-09-19

No sustituye el cierre funcional inferior ni cambia su huella. Se consolida la
continuidad existente y se conecta al panel Sentinel; no otra cola o scheduler.

- CONVERSATION_INDEX recoge diez temas de fuentes dentro del proyecto, con decisiones, implementaciones, autoridad desplazada y pendientes. No se consultaron ni inventaron chats externos.
- CURRENT_TRUTH, ACTIVE_WORK, CODEX_QUEUE, MASTER_CONTROL y ROADMAP dejan de presentar septiembre 9 como vigente. DECISIONS, BLOCKERS y RELEASE_STATE concentran sus responsabilidades. Una cola, 23 IDs unicos; aliases preservados.
- Copias anteriores: data/local_dev/organization-20260919/before. No se movio ni elimino evidencia; los estados historicos siguen recuperables en Git y NEMESIS_CONTROL_PROYECTO.
- Sentinel /admin/sentinel-issues -> Proyecto y continuidad: busqueda, filtros, responsables, bloqueos, candidatos/versiones, fuentes abiertas dentro del panel e inventario fechado. Lectura no crea jobs ni cambia incidencias.
- HEAD se lee de metadatos Git. Si contradice RELEASE_STATE se muestra conflicto. Documentacion/archivo presente no equivale a QA ni produccion; diff local no se certifica por HEAD.
- Cuatro worktrees y siete ramas observados: main limpio; Sentinel activo; Design 4401 y documental 6131 registros dirty, ambos PRESERVE. Cero worktrees/ramas retirados.
- Inventario acotado a archivos del candidato y metadatos Git de los otros worktrees: 2168 documentos (17 CANONICAL, 5 ACTIVE, 1831 EVIDENCE, 24 HISTORICAL, 1 SUPERSEDED, 290 UNKNOWN). UNKNOWN conserva contenido y requiere revision, no se fuerza a cero.
- 61 grupos documentales byte-identicos conservados. Metadatos de 1011 caches, 305 DB/sidecars, 18 logs, 84 evidencias QA, 16 paquetes/parches y 2 archivos de entorno retenidos. No se leen bytes de DB, logs ni .env. No es un inventario fisico exhaustivo de Design/OneDrive.
- Legacy: cero motores con ausencia de import estatico tras separar inicializadores; 20 templates sin referencia literal, 135 grupos de aliases del mismo handler y 16 grupos de helpers con cuerpo igual. No prueban ausencia de consumidores dinamicos/CLI. SAFE_TO_RETIRE=0; cuatro gates obligatorios antes de retirar.
- Esta fase cambia 20 archivos respecto al cierre previo (incluido este informe); el candidato acumulado tiene 108 rutas modificadas/nuevas. Manifest anterior preservado en organization-20260919/prior-source-manifest.json.
- Huella de fuentes de esta fase: b511256f82f06b48e2bb930f4c7728f72aeab288652a91ca6fb9db86a4da38d3. No es SHA Git ni certificacion productiva.
- QA final: 768 PASS, 0 FAIL/ERROR/SKIP, 55.060 s; incluye los 742 anteriores y 26 casos nuevos, NO se suman ambas ejecuciones. XML: data/local_dev/organization-20260919/final-c7788af41cfa4d719639f10ba582dc35/result.xml.
- Navegador Flask real: 13 fuentes, filtros, recarga y segunda pestana; 0 jobs creados por lectura. 1366/390/430 y texto 200% a 430 sin overflow observado, 0 errores JS ni requests externas. Capturas y browser.json en organization-20260919. Inyeccion de texto malicioso es caso sintetico separado, no fuente real.
- Fallos intermedios: POST sin CSRF correctamente devolvia 403 antes del 405 de metodo; se mantiene caso negativo y se comprueba 405 con CSRF valido. El service worker interceptaba la sonda sintetica del arnes; se bloquea solo en ese contexto Playwright para observarla, sin cambiar seguridad ni PWA del producto.
- 202 Jinja, compilacion y Secret/Privacy Guard: PASS local; 1164 archivos escaneados, 0 hallazgos. Los 43 bloqueos historicos siguen sin recertificar.
- Main y Design sin editar; sin staging, commit, push, PR, merge, deploy ni costes. Frentes funcionales y automatizaciones no se suspenden. Organizacion operativa implementada; clasificacion/retirada legacy completa sigue pendiente, no se declara todo cerrado.

Reanudar desde la cola unica y la huella, sin otra auditoria masiva. Revisar
UNKNOWN y consumidores solo cuando afecten una retirada concreta. Conservar
pendientes funcionales de arte/datos/comercial en sus IDs existentes.

## Base y preservacion

- Worktree: `C:\Users\aloha\.codex\worktrees\nemesis-sentinel-operaciones`.
- Rama: `codex/sentinel-operaciones-local`. HEAD/base: `c4a81003de1b5ccdb3036831583e9c1eb65e4417`.
- Main limpio. No staging, commits, push, PR, merge ni deploy realizados.
- Design `317ac8c37c3c74f39b736a207f55079c7d454856` permanece sin editar. No se ejecuta su app incompleta.
- R8 se recupera por diferencias versionadas, no copiando el arbol entero. R9 no certificado.
- PR14 remoto confirmado borrador `ef759cb88d46463424342598a765a68a0a057a7a`; objetos ya disponibles localmente. Se adapta el consumidor sin cambiar las ramas remotas. PR12 no incorporado por inercia.
- ZIP/parche Sentinel anunciado NO recibido: su SHA no se certifica. Implementacion local independiente sobre panel y ejecutor existentes.
- App Icon, fallback de escudos, Sports Truth y SPORTS_DATA_LIVE_CERTIFICATION.md conservan blobs HEAD. No se reanuda DAY 3-7.

## Mejoras utilizables

1. Sentinel: antes no habia una solicitud durable ejecutable desde este panel; ahora `/admin/sentinel-issues` solicita la revision estatica acotada de ocho plantillas mediante Product Experience Worker. Flask valida admin/CSRF/accion/parametros; SQLite conserva job_id, revision, intento y resultado. GET consulta. No cierra incidencias ni certifica funcionalidad por ausencia de hallazgos.
2. R8: Home, Calendario, Match Center, idiomas y soporte recuperados en copia completa sin retroceder Design. Se mantiene el recorrido Home -> Calendario -> partido -> retorno, ES/EN/FR y hora Madrid.
3. Directo: consumidor PR14 adaptado a la localizacion R8, caducidad LIVE, cero/minuto/score nullable, foco y enlaces conservados. Se elimina el corte visual a cinco tarjetas; doce filas probadas. Esto no demuestra cobertura universal del proveedor ni elimina limites de catalogo backend.
4. Que ha cambiado: actualizacion observada de marcador se muestra como SCORE_UPDATE; no se afirma GOAL sin evento. No hay nueva persistencia de ultima visita ni otro motor.
5. Soporte: envio local -> persistencia -> bandeja admin comprobado en navegador. No email externo, respuesta humana ni entrega productiva certificados.
6. Membresias: cuatro defectos reproducidos antes de corregir: alta/cancelacion reemplazaba concesion manual, alta podia reemplazar rol ADMIN, cancelacion de suscripcion anterior podia retirar acceso actual. Correccion local conserva historial y no cambia concesion/rol ajenos; cancelacion vigente y cancelacion al final de periodo mantienen comportamiento probado. Sin Stripe externo.
7. Sentinel visual: la captura completa detecto secciones heredadas encajadas como main/aside, con filtros estrechos e indicadores estirados. Se restablece el ancho de seccion y se evita scroll horizontal en el resumen; navegador comprueba estos limites en escritorio y movil. No se declara conformidad visual global.

## QA de este arbol

- Huella de fuentes (excluye documentacion): `8dcdaa1e933a92d0661052d38f0cb3881d5900e1ea7f60bba9dfb9b142959dd8`.
- Manifest por archivo/origen/ambito/hash: `data/local_dev/final-source-manifest.json`. R8/PR14/local se distinguen; no se atribuyen todos los cambios a esta sesion desde cero.
- Diff final: 95 archivos; 61 producto, 25 pruebas, 6 herramientas y 3 documentos. Indice vacio.
- 742 pruebas transversales finales: 742 PASS, 0 FAIL/ERROR/SKIP, 52.013 s. XML: `data/local_dev/candidate-final-eafe0553050341a1853357aa6e714cd3/result.xml`. La ejecucion anterior queda preservada, no se suma como cobertura nueva.
- 13 registro/concurrencia: PASS, dos procesos, reclamacion atomica, idempotencia, aislamiento, error saneado, lease y no reintento automatico. XML: `data/local_dev/sentinel-unit-final.xml`.
- 45 aperturas cliente + 27 vistas (ES/EN/FR, 1366/390/430, Tokyo/New York/London), sin errores JS, overflow detectado ni requests externas: `data/local_dev/journeys-893fc40045fd47d99dbad2f5d1bc3c61/result.json`.
- Sentinel navegador: Flask HTTP real, segundo tab y recarga mismo job/attempt 1; `data/local_dev/sentinel-browser/result.json`. Capturas 1366/390/430 y ampliacion de texto.
- Reinicio del supervisor: tres resultados anteriores identicos; checkpoint RUNNING de QA -> INTERRUPTED, intento 1, sin retry: `data/local_dev/restart-result.json`. El checkpoint es inyectado en DB QA; no se afirma una interrupcion observada en produccion.
- Directo: pruebas de componente con transporte en memoria y pruebas Flask reales con respuestas interceptadas por Chromium. Son SIMULATED_QA, no feed deportivo ni certificacion externa.
- 201 plantillas Jinja analizadas; compileall/py_compile, diff-check, Secret/Privacy Guard sin hallazgos en 1158 archivos del alcance escaneado.
- Fallos intermedios conservados en XML: dependencias de inspector R8, helpers i18n, ruta de log, UTF-8 y configuracion del arnes/navegador corregidos. No se cambiaron expectativas deportivas ni se usaron skips para obtener verde.
- Un arranque final de pytest tambien fue bloqueado antes de ejecutar pruebas por la ruta de log predeterminada fuera del area QA. Se especifico el log dentro del directorio temporal permitido, sin cambiar la frontera de escritura. No se contabiliza como prueba aprobada.
- Los 43 bloqueos historicos no se convierten en PASS: esta es una seleccion transversal nueva, no toda la suite global anterior.

## Diseno y limites

Se abrieron las 16 referencias; REF-12 sigue siendo Match Center. H01-H06/H08-H09
se conservan segun cierre historico, sin atribuirles recertificacion exhaustiva.
H07/identidad artistica sigue pendiente. No se regenero arte ni se modifico el icono.
No se declara DESIGN_MATCH global: composicion, intensidad artistica, datos completos
y superficies no cubiertas siguen necesitando comparacion concreta.

/app: nueve lecturas HTTP locales 0.09-0.23 s. No reproduce ni resuelve el timeout
productivo del 15/09. P50/P95 productivos: INSUFFICIENT_SAMPLE.

Pendientes concretos: cobertura/rights/cuota/feed reales autorizados; limites de
catalogo y resultados completos; PR12 y parche unificado no integrados a ciegas;
validacion artistica; ELITE+ sin contrato en catalogo; webhook/pagos reales,
renovaciones externas y fiscalidad antes de activacion comercial; integracion
productiva del supervisor (actualmente solo LOCAL SAFE). No otro scheduler.

## Abrir y reanudar

Vista previa supervisada: `http://127.0.0.1:54910`, solo loopback.
Acceso temporal local en `data/local_dev/sentinel-preview.json`; no es credencial
productiva. Panel: `/admin/sentinel-issues`. Cliente: `/app`.

Reanudar sin inventario masivo: comprobar solo HEAD/indice y manifest, verificar
si el PID de sentinel-preview.json sigue siendo el supervisor propio. Los datos
de QA estan en data/local_dev, nunca en la DB real. Comando reproducible:
`tools/local_desktop/run_sentinel_local.py --port 54910` con el Python ya verificado.

Ediciones congeladas al cierre. Proximo paso minimo: revisar este candidato local
y resolver los limites concretos de arte/datos/activacion antes de autorizar una
integracion o publicacion. No activar las filas de la cola automaticamente.
