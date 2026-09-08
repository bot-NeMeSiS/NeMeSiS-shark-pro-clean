# Estado Actual del Proyecto

## Vigencia local 2026-09-07: continuidad A/B

Base real de esta ejecucion: `main`, HEAD
`4df7fc20e3de9cbe84d2098f3d6b3a74577631f5`, indice sin staging.
No se han consultado GitHub/Render en este encargo; las referencias inferiores
son historicas, no una nueva comprobacion de produccion.

Candidato local: lectura admin acotada, bootstrap sin solapamiento y snapshot
historico que distingue NULL de cero y no colisiona entre ejecuciones.
527/527 tests del arbol final; 52 observaciones focales de navegador A/B.
Global PARCIAL: primera visita local escribe perfil/cache/estado; no se ha
modificado esa logica sensible ni certificado proveedor real o derechos historicos.
DAY 3 y DAY 4 intactos. Arte SHARK/fondo pendiente humano. Sin publicacion.

Unico cierre y evidencia: [informe A/B](../reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md).
El tablero existente recoge NEM-01/02/03/04/05/08/09/10/11 sin duplicar tareas.

Conciliacion vigente: 2026-09-06 (Europe/Madrid).

## Decision ejecutiva

El conjunto funcional desplegado y verificado sigue identificado por
`6295222a3cd0c77c8ebd3ac8c304017d7b93ca8b`. El HEAD local y la referencia local
de `origin/main` son `8ab59a16b6dd0ae69727547c78709d012b4d3fb7`, un hijo que solo
actualiza estos documentos de control. El SHA productivo no se ha vuelto a
consultar en esta reconciliacion CI.

Sobre ese HEAD existe una reparacion local, no staged y no publicada, para
reconciliar `tools/check_v937_sports_lifecycle.py` con el contrato Sports Truth
vigente. Afecta de forma intencionada a `app.py`,
`engines/v935_launch_trust_engine.py`, el check V937 y sus regresiones
permanentes; este documento registra la evidencia sin convertirla en resultado
remoto.

`6295222a` es hijo directo de `46dbe05d81928248284580b66cfbf2a006fcf3e2`.
El padre incorporo reutilizacion por peticion para dashboard/picks/usuario y un
diagnostico deportivo separado por ejecucion, acceso, plan, cuota, cobertura y
frescura. El hijo incorporo Match Context factual, H2H, forma, clasificacion y
su integracion en Match Center. No se reinicio Match Context ni se creo un motor
paralelo.

## Estado por evidencia

| Ambito | Integrado | Desplegado | Probado localmente | Verificado en produccion |
|---|---|---|---|---|
| Dashboard runtime | SI | SI | PASS | PENDIENTE `/app` autenticado |
| Diagnostico deportivo | SI | SI | PASS | Estructura observada; datos/frescura real no recertificados |
| Match Context | SI | SI | PASS | SHA/health PASS; comportamiento autenticado PENDIENTE |
| Sports Truth | SI | SI | PASS | Sin regresion en logs/smoke; LIVE real sigue en certificacion 3-7 dias |
| Madrid Time | SI | SI | PASS | No revalidado con navegador autenticado |
| Permisos cliente/admin | SI | SI | PASS aislado | PENDIENTE por falta de sesion/navegador utilizable |
| Reconciliacion CI Sports Truth | CAMBIO LOCAL | NO | 458/458 PASS | NO EJECUTADA EN GITHUB/PRODUCCION |

## Integracion de `app.py`

Los dos incrementos comparten el archivo, pero no se sobrescriben:

- `46dbe05d` modifica `_build_sports_pipeline_diagnostics`, payload de cron,
  `get_picks`, `published_picks_for_user`, contextos de favoritos/briefing,
  `current_session_user` y `dashboard_data`.
- `6295222a` modifica `_cached_h2h_for_match`,
  `_cached_match_standings`, `_competition_standings_for`,
  `recent_team_form` y la composicion del detalle de partido.
- Ninguna funcion modificada por el padre fue reemplazada por el hijo.
- La cache de picks sigue limitada a GET/HEAD y a `flask.g`; su clave conserva
  DB, usuario, rol, membresia, filtros, acceso admin y fecha Madrid, y devuelve
  copias profundas.
- La cache de usuario sigue limitada a la peticion, valida la identidad de
  sesion y conserva expiracion de membresia y separacion ADMIN.
- Match Context importa y delega en `match_status_truth`; no promueve horario,
  score o cache a LIVE y oculta minuto cuando Sports Truth no confirma LIVE.

## QA exacta del conjunto

Se materializo el commit exacto mediante `git archive` fuera del repositorio.
La ejecucion valida uso SQLite privado, jobs desactivados, claves externas
vacias y bloqueo explicito de conexiones salientes; no uso datos reales.

- Suite historica del conjunto `6295222a`: **456/456 PASS**.
- Suite completa del HEAD `8ab59a16` mas la reparacion local: **458/458 PASS**.
- Matriz focal dashboard + diagnostico + Match Context + permisos + Madrid Time
  + Competition Identity + Sports Truth: **75/75 PASS**.
- Conexiones externas: **0**.
- La primera tentativa de suite se descarto: pytest no podia escribir en su
  carpeta temporal y LOCAL SAFE bloqueo correctamente dos secretos sinteticos.
  Se repitio con `--basetemp` privado y bloqueo de socket independiente.
- No se modificaron DB real, usuarios, membresias, proveedores, cron, Telegram,
  Stripe ni secretos.

## Reconciliacion `CI_SPORTS_TRUTH_GATE`

El check V937 se reprodujo primero en una materializacion exacta y privada de
`8ab59a16`, con DB temporal, jobs desactivados, claves vacias y sockets
salientes bloqueados. Resultado inicial: **14 errores**, sin llamadas externas.

| # | Error reproducido | Clasificacion | Resolucion local |
|---:|---|---|---|
| 1 | marcador `live.html:lifecycle_story` | ACOPLAMIENTO_VISUAL_OBSOLETO | Comprueba el KPI vigente `live_confirmed`. |
| 2 | copy SHARK antiguo | ACOPLAMIENTO_VISUAL_OBSOLETO | Comprueba el texto factual vigente. |
| 3 | `Match Finished` sin score esperado como final | FIXTURE_INSUFICIENTE | Sin score queda `RESULT_PENDING`; con score confirmado queda `FINALIZADO`. |
| 4 | minuto `63` usado como prueba de LIVE | EXPECTATIVA_ANTIGUA | El minuto aislado no promociona a LIVE. |
| 5 | `Match Postponed` no reconocido | REGRESION_FUNCIONAL | Alias largo normalizado como `SUSPENDIDO`, nunca LIVE. |
| 6 | 0-0 mas `updated_at` esperado como LIVE | FIXTURE_INSUFICIENTE | El fixture fresco usa `last_synced_at`. |
| 7 | LIVE generico sin evidencia esperado como incompleto | EXPECTATIVA_ANTIGUA | Falla cerrado como `STALE`. |
| 8 | V935 0-0 mas reloj generico esperado como LIVE | FIXTURE_INSUFICIENTE | Score y write local no prueban LIVE. |
| 9 | V934 LIVE generico esperado como pendiente | EXPECTATIVA_ANTIGUA | Se conserva `STALE`, no publicable. |
| 10 | catalogo publico sin fixture fresco | RELOJ_INCOHERENTE | Snapshots usan un mismo reloj fijo y procedencia canonica. |
| 11 | LIVE fresco ausente | RELOJ_INCOHERENTE | `last_synced_at` coherente a 30 segundos. |
| 12 | diagnostico stale ausente | RELOJ_INCOHERENTE | Caso stale coherente a 121 segundos. |
| 13 | intervalo de polling fresco ausente | RELOJ_INCOHERENTE | Derivado del mismo snapshot fresco. |
| 14 | LIVE SportsDB confirmado no persistido | FIXTURE_INSUFICIENTE | Persistencia recibe evidencia temporal canonica. |

La investigacion del caso 3 encontro ademas una regresion funcional real en el
adaptador: `sportsdb_match_status` descartaba `intHomeScore/intAwayScore`. El
adaptador ahora pasa esos scores al motor canonico. Se anadieron regresiones
permanentes para final confirmado con score y para el alias largo de aplazado.
No se rebajo Sports Truth: un LIVE confirmado y reciente se publica; un LIVE
sin reloj canonico o desactualizado permanece fuera del catalogo publico.

### Controles locales ejecutados

- Import, `py_compile`, `compileall`: PASS.
- Jinja: **199/199 PASS**.
- V937 Sports Lifecycle corregido: PASS.
- Madrid Time, workforce V915, Product Update V937, Calendario V940, Match Live
  Story, Master Operating System y pipeline V937: PASS.
- Navegacion: **926 enlaces / 245 clicks PASS**; worker: **807 rutas / 1089
  enlaces**, 0 rotos, 0 loops y 0 botones muertos.
- Sentinel: **10.0 PASS**, 0 incidencias.
- Secret Guard: **1103 archivos**, 0 hallazgos.
- Imports/routes: **744 rutas**, sin templates ni assets ausentes.
- Route/link audit: **807 rutas**, `unsafe_smoke=0`; conserva 21 enlaces API
  directos ya registrados como deuda de presentacion.
- Suite combinada: **458/458 PASS**. Dos sondas LAN sinteticas hacia `8.8.8.8`
  fueron bloqueadas por el arnes; conexiones externas completadas: **0**.

El entorno local usa Python 3.12, mientras el workflow declarado usa Python
3.11.9. No se observo incompatibilidad, pero el PASS local no sustituye una
nueva ejecucion de GitHub.

### Preflight restante

Todos los controles posteriores ejecutables pasan salvo
`tools/check_v944_match_center_foundation.py`, que termina con
`Browser QA result missing`. El contrato estatico V944 pasa; el bloqueo es de
orquestacion CI: el check exige
`browser_qa/V944_MATCH_CENTER_FOUNDATION/browser_qa_result.json`, un artefacto
deliberadamente no versionado, pero el preflight no ejecuta antes el Browser QA
que lo genera ni dispone de un seed reproducible para sus dos fixtures. No se
ha eliminado ni relajado el check. Es un bloqueo independiente que apareceria
despues de reparar V937 en un checkout limpio.

## Rendimiento comparable de `/app`

Benchmark autenticado local con el mismo arnes, entradas, permisos y reloj fijo
`2026-09-06T12:00:00+02:00`; 0, 50 y 500 picks, una pasada fria y dos calientes.
Son muestras locales, no latencia productiva ni P95.

| Picks | Padre `46dbe05d` frio / calientes | Combinado `6295222a` frio / calientes |
|---:|---:|---:|
| 0 | 466 / 194 / 129 ms | 436 / 195 / 134 ms |
| 50 | 1217 / 775 / 720 ms | 1368 / 740 / 694 ms |
| 500 | 6134 / 2304 / 2133 ms | 6409 / 2225 / 2175 ms |

Las nueve respuestas fueron HTTP 200, con `network_attempts=0`. Los hashes
semanticos y todos los contadores instrumentados coinciden entre padre y
combinado. En 500 picks se conservan: `get_picks` 8 frio/7 caliente,
`pick_quality_score` 407/207, lecturas SQL 2036/1100, briefing 1 y smart board 1.
La variacion temporal observada no demuestra regresion; el trabajo ejecutado es
identico y las pasadas calientes varian entre -4,5 % y +3,8 %.

La reconciliacion CI repitio el mismo escenario de 0/50/500 picks, usuario QA,
reloj fijo y tres peticiones sobre materializaciones privadas de `8ab59a16` con
y sin el parche. Los bytes de respuesta y el usuario visible coincidieron en
cada volumen; las nueve respuestas por arbol fueron HTTP 200 y no hubo intentos
de red.

| Picks | `8ab59a16` frio / calientes | Reparacion local frio / calientes |
|---:|---:|---:|
| 0 | 411 / 115 / 105 ms | 712 / 105 / 109 ms |
| 50 | 1377 / 823 / 827 ms | 1368 / 820 / 832 ms |
| 500 | 4981 / 2879 / 2929 ms | 5176 / 2933 / 2929 ms |

La primera muestra de 0 picks contiene ruido de inicializacion; las pasadas
calientes y los escenarios 50/500 no muestran una regresion funcional ni una
amplificacion de trabajo atribuible al parche.

## Produccion realmente comprobada

- Render web: deploy `dep-daeq2r67bikc73djups0`, `LIVE`, SHA `6295222a`.
- Render cron: deploy `dep-daeq2r67bikc73djurk0`, `LIVE`, SHA `6295222a`.
- `/api/health`: HTTP 200, `ok=true`.
- `/api/runtime-version`: HTTP 200, SHA exacto, archivos de version alineados y
  `active_errors_count=0`.
- `/version`: HTTP 200.
- Logs desde el deploy: 0 `error/critical`, 0 respuestas 5xx y 0
  `WORKER TIMEOUT` en la ventana consultada.
- `/app` autenticado y clicks de navegacion: **PENDIENTE**. La herramienta de
  navegador no pudo iniciar; no se creo usuario, no se extrajeron credenciales
  y no se uso un redirect como sustituto de la prueba.

## Advertencia `runtime-version`

La muestra historica de 10,96 s sigue siendo una advertencia aislada, no P95 ni
regresion confirmada. Una lectura productiva actual tardo 5,41 s. El mismo
endpoint en local aislado tardo 365 / 205 / 202 ms y devolvio HTTP 200.

El recorrido local lee `app.py`, varias hojas CSS, plantilla base y numerosos
resumenes runtime antes de construir un payload de unos 40,8 KB. Esto explica
una superficie de trabajo amplia, pero no prueba por si solo la causa de la
latencia Render. No se hicieron sondeos intensivos.

## Datos y limites vigentes

- No se llamo a `/api/live`, sync, cron, test-send, proveedores ni pagos.
- La disponibilidad, cuota, cobertura y frescura deportivas reales no se
  recertificaron en este encargo; no deben inferirse del health HTTP.
- DAY 3 permanece intacto en `SPORTS_DATA_LIVE_CERTIFICATION.md`, SHA-256
  `BD6FD290282682986F626FB966127F9B56D6310DC970A3DA90207B8D4AFBD642`.
- La certificacion Sports 3-7 dias continua; no se inventa un partido LIVE.
- El informe `reports/DASHBOARD_RUNTIME_AND_SPORTS_DIAGNOSTICS_REPAIR.md` se
  conserva como evidencia historica de su fase local y no se reescribe.

## Excepcion de publicacion GitHub

El registro del push normal anterior identifica reglas que exigian PR, tres
checks (`preflight`, `qa`, `smoke`) y alcance de enforcement `non_admins`.
La cuenta con capacidad administrativa pudo publicar y GitHub informo la
excepcion. No se uso `--force` ni una opcion explicita de bypass.

Para `6295222a` SI existen ejecuciones observadas:

- `qa`: **SUCCESS**.
- `smoke`: **SUCCESS**.
- `preflight`: **FAILURE**.
- `certify-production`: **SKIPPED**, consecuencia de la dependencia fallida.
- Run: `34048426812`; job `preflight`: `101527550445`.

El fallo historico se conserva. La reparacion V937 solo tiene PASS local y no se
ha repetido Actions remotamente.

Proxima entrega recomendada: rama dedicada, PR a `main`, ejecucion obligatoria
de `preflight`, `qa` y `smoke`, revision de resultados y merge normal. Revisar
que la proteccion se aplique tambien a administradores; no cambiar enforcement
ni permisos dentro de este encargo.

## Siguientes acciones (maximo tres)

1. Integrar una generacion Browser QA V944 reproducible en CI antes de su check,
   sin versionar resultados ni rebajar el gate.
2. Cuando exista autorizacion de publicacion, usar rama + PR y exigir
   `preflight`, `qa` y `smoke` antes del merge normal.
3. Continuar Sports DAY 3-7 sin reiniciar ni reinterpretar DAY 3.

## Operaciones de este encargo

Commit: NO. Push: NO. Merge: NO. Deploy: NO. Render writes: NO. Produccion,
tareas, secretos y datos reales: SIN CAMBIOS.

## Cierre visual local completo - 2026-09-07

Estado: **PASS TECNICO LOCAL / REVISION VISUAL HUMANA PENDIENTE**.

- Base preservada: `8ab59a16b6dd0ae69727547c78709d012b4d3fb7`; `HEAD` y
  `origin/main` continuan alineados. Produccion no se consulto ni modifico.
- Referencias: las 16 PNG canonicas de `reference_images` fueron abiertas,
  inventariadas y comparadas con capturas reales de la app local. No se uso
  codigo, payload ni CSS historico de `REFERENCE_ONLY`.
- Causa visual corregida: fondo excesivamente plano/cian, tiburon atmosferico
  demasiado lleno y generico, Home con jerarquia deportiva tardia, estados
  vacios sobredimensionados y densidad movil mejorable.
- Implementacion: composicion oceanica por capas en la autoridad CSS existente,
  geometria nueva del tiburon atmosferico, separacion conservada respecto al
  tiburon de marca, Home sports-first, estados vacios compactos y cache busting
  actualizado. No se anadio una hoja CSS nueva ni un muro de `!important`.
- Evidencia browser final:
  `.tmp_reference_review/visual_full_20260906/full_release2/PQA-20260907004915`.
  Resultado PASS; 171 capturas, 54 clics/taps reales sin fallo, 9/9 journeys,
  0 errores de consola, 0 page errors, 0 llamadas a proveedores y 0 mutaciones
  de produccion.
- Componentes: 7.742 instancias auditadas; 0 fallos y 0 overflow. Composicion:
  0 dead-space flags, 0 empty-dashboard flags y profundidad maxima de cards 1.
- Comparacion de referencias: 75 `MATCH`, 33 `MINOR_GAP`, 0 `MAJOR_GAP` y
  0 `FAIL`. Paquete privado de revision:
  `.tmp_reference_review/visual_full_20260906/founder_package/`.
- Limite visual honesto: la referencia oficial presenta un tiburon mas
  volumetrico y fotorrealista. El SVG propio actual aproxima silueta, escala,
  posicion, malla e iluminacion con un asset ligero, pero la aprobacion de marca
  sigue siendo una decision humana; no se declara pixel-perfect.
- QA reproducida sobre el arbol combinado: pytest 458/458, Jinja 199/199,
  smoke Flask 29/29, imports/rutas 744, V937 Sports Lifecycle PASS, Madrid Time
  PASS, Sentinel estatico 10/10 sobre 39 rutas y Privacy/Secret Guard PASS sobre
  1.104 archivos. El primer pase con variables globales forzadas produjo ruido
  entre tests; el pase final limpio es la evidencia vigente.
- Rendimiento: gate browser PASS, maximo `page_ready_ms=3571` en 171 muestras.
  Las hojas activas pesan 216,1 KiB gzip; se conserva como warning de deuda CSS,
  sin regresion funcional demostrada ni purga global dentro de este alcance.
- Sports Truth, Match Context, aislamiento por peticion, documentacion previa y
  `SPORTS_DATA_LIVE_CERTIFICATION.md` DAY 3 conservaron sus hashes respecto al
  manifiesto previo al trabajo visual.
- Enlaces: 199 templates escaneados, 0 `href="#"`, 0 `javascript:void`, 0
  formularios sin contrato y 0 fallos en clics reales. Los 21 enlaces directos
  admin/automation ya conocidos siguen siendo deuda de presentacion, no un
  fallo funcional nuevo.
- Publicacion: commit NO, staging NO, push NO, merge NO, deploy NO. Proveedores,
  Render, DB real, usuarios, membresias, Telegram, Stripe y secretos: sin cambios.
