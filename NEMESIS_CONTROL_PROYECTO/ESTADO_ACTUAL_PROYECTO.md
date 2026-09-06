# Estado Actual del Proyecto

Conciliacion vigente: 2026-09-06 (Europe/Madrid).

## Decision ejecutiva

El conjunto actual esta integrado, desplegado y probado localmente en el commit
`6295222a3cd0c77c8ebd3ac8c304017d7b93ca8b`. `main` local, `origin/main` y el
runtime de Render apuntan al mismo SHA. El arbol estaba limpio antes de esta
conciliacion; los unicos cambios locales posteriores son estos documentos de
control y no estan preparados para commit.

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

- Suite completa: **456/456 PASS**.
- Matriz focal dashboard + diagnostico + Match Context + permisos + Madrid Time
  + Competition Identity + Sports Truth: **75/75 PASS**.
- Conexiones externas: **0**.
- La primera tentativa de suite se descarto: pytest no podia escribir en su
  carpeta temporal y LOCAL SAFE bloqueo correctamente dos secretos sinteticos.
  Se repitio con `--basetemp` privado y bloqueo de socket independiente.
- No se modificaron DB real, usuarios, membresias, proveedores, cron, Telegram,
  Stripe ni secretos.

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
excepcion. No se uso `--force` ni una opcion explicita de bypass. Para
`6295222a`, GitHub no expone status checks ni workflow runs asociados en la
consulta actual.

Proxima entrega recomendada: rama dedicada, PR a `main`, ejecucion obligatoria
de `preflight`, `qa` y `smoke`, revision de resultados y merge normal. Revisar
que la proteccion se aplique tambien a administradores; no cambiar enforcement
ni permisos dentro de este encargo.

## Siguientes acciones (maximo tres)

1. Repetir `/app` y navegacion real en produccion solo cuando exista una sesion
   ya autorizada y un navegador operativo.
2. Adoptar PR + checks obligatorios para la proxima publicacion y confirmar el
   alcance de `enforcement` con un propietario del repositorio.
3. Continuar la certificacion Sports DAY 3-7 y perfilar `runtime-version` solo
   si nuevas muestras productivas confirman latencia sostenida.

## Operaciones de este encargo

Commit: NO. Push: NO. Merge: NO. Deploy: NO. Render writes: NO. Produccion,
tareas, secretos y datos reales: SIN CAMBIOS.
