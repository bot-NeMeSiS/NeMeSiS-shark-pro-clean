# Dashboard runtime and sports diagnostics repair

## Decision ejecutiva

Estado: **VALIDADO LOCALMENTE**.

Este trabajo reduce de forma demostrable el calculo repetido dentro de una sola
peticion autenticada a `/app` y separa el diagnostico deportivo en ejecucion,
acceso, cuota, cobertura y frescura. No se ha desplegado ni se ha verificado el
parche en produccion.

El `WORKER TIMEOUT` observado en produccion el 6 de septiembre de 2026 no se
reprodujo como aborto o respuesta 500 en local. La amplificacion de trabajo si se
reprodujo con datos sinteticos aislados y es un contribuyente plausible, no una
causa raiz productiva confirmada.

## A. Base local y alcance

- Rama: `main`.
- HEAD local: `419a04d84ca92c021d7610ca15f4d62ccfaba76b`.
- `origin/main`: `419a04d84ca92c021d7610ca15f4d62ccfaba76b`.
- Version conservada: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`.
- Indice Git: vacio antes y despues de las pruebas.
- Commit, push, merge, deploy y cambios Render: **NO**.
- DB real, proveedores, `/api/live`, Telegram, Stripe y automatizaciones reales:
  **NO TOCADOS**.

Archivos modificados por esta reparacion:

- `app.py` (archivo compartido; se conservaron los cambios previos de Match Context).
- `engines/picks_quality_engine.py`.
- `tools/render_cron_master_tick.py`.
- `tests/test_render_cron_master_tick.py`.
- `tests/test_dashboard_runtime_sports_diagnostics_repair.py` (nuevo).
- `reports/DASHBOARD_RUNTIME_AND_SPORTS_DIAGNOSTICS_REPAIR.md` (este informe).

Los cambios anteriores de Match Context, sus tests y los tres documentos del
centro de control ya modificados estaban presentes en el preflight. Sus hashes,
salvo `app.py` por ser compartido, coinciden con el snapshot previo de esta
reparacion.

Snapshot recuperable previo, fuera del repositorio: 13 archivos pertinentes y
manifiesto privado con SHA-256
`0667210773538FABCAAFE136D040AEC1D554482BE89190E14FD009333A72A78C`.
No contiene DB, secretos ni una copia completa del workspace.

## B. Dashboard autenticado: evidencia y correccion

### Evidencia reproducida

El arnes uso:

- peticion autenticada real al handler `/app`, con contexto completo y Jinja;
- reloj fijo `2026-09-06T12:00:00+02:00`;
- DB SQLite sintetica y aislada fuera del repositorio;
- volumenes 0, 50 y 500 picks;
- tres repeticiones por volumen: una fria y dos calientes;
- credenciales externas vacias, jobs desactivados y conexiones salientes
  bloqueadas;
- `network_attempts=0`.

No hubo timeout ni 500 local: todas las peticiones devolvieron HTTP 200 y el
usuario autenticado correcto. El escenario grande, no obstante, demostro una
amplificacion severa de enriquecimiento, puntuacion, localizacion y lecturas SQL.

### Antes y despues

Los tiempos son muestras locales observadas, no P95 de produccion. La base fue
una materializacion exacta de `HEAD` y el despues fue una materializacion exacta
del candidato publicable de seis rutas. Ambos usaron las mismas entradas,
permisos, reloj, DB aislada y bloqueo de red. El arnes de base trato como
opcionales los dos helpers que solo existen en el parche; no cambio el flujo del
producto.

| Picks | HEAD frio | HEAD caliente | Candidato frio | Candidato caliente |
|---:|---:|---:|---:|---:|
| 0 | 507 ms | 286 / 249 ms | 385 ms | 180 / 112 ms |
| 50 | 2970 ms | 2245 / 2158 ms | 1429 ms | 773 / 754 ms |
| 500 | 9113 ms | 4869 / 4816 ms | 6256 ms | 2356 / 2103 ms |

Trabajo observado en el escenario de 500 picks:

| Operacion | Antes frio / caliente | Despues frio / caliente |
|---|---:|---:|
| `get_picks` | 16 / 15 | 8 / 7 |
| `enrich_pick_quality` | 1778 / 1378 | 407 / 207 |
| `pick_quality_score` | 5132 / 3980 | 407 / 207 |
| `_valid_selection` | 10466 / 8114 | 1221 / 621 |
| `spanish_competition_name` | 43810 / 29810 | 14274 / 5258 |
| `spanish_team_name` | 62244 / 35932 | 36108 / 13180 |
| `build_daily_briefing` | 2 / 2 | 1 / 1 |
| `smart_pick_board` | 3 / 3 | 1 / 1 |
| lecturas SQL | 2473 / 1531 | 2036 / 1100 |

Los hashes semanticos fueron identicos antes y despues con las mismas entradas:

- volumen 0: `169b2d0f93c23ad4a52eaf4200e995114d30c404c01b6b37063e6edca771e9b2`;
- volumen 50: `47c81dbed6e9dd9cd67ee7a4873e5ce5b266263113ef36cfea4b9fa291d29d6d`;
- volumen 500: `f79bdab479d6046ae51e843632022796dd2063b94ce2f5d9a32361ea60672afb`.

### Correccion aplicada

- La calidad se calcula una vez por pick y se reutiliza para bucket, orden y split.
- Se separaron helpers para ordenar/dividir picks ya enriquecidos, manteniendo los
  helpers publicos compatibles.
- `get_picks` normaliza estados una vez y dispone de reutilizacion estrictamente
  acotada a la peticion GET/HEAD. La clave incluye DB, usuario, rol, membresia,
  limite, estado, filtro, acceso admin y fecha Madrid.
- La cache vive en `flask.g`, nunca es global ni persistida, y entrega copias
  profundas para evitar compartir estructuras mutables.
- El usuario de sesion se resuelve una vez por peticion y conserva expiracion de
  membresia, aislamiento admin y cambio de identidad.
- Dashboard, briefing, command center, favoritos, alertas, actividad, Telegram y
  smart picks reutilizan contextos ya calculados dentro de la misma peticion.

Las regresiones prueban FREE, PRO, ELITE y ADMIN conforme al contrato actual. Dos
usuarios PRO distintos no mezclan datos y ADMIN permanece aislado. `ELITE+` no es
un rol vigente de la aplicacion y no se ha creado uno nuevo.

Tambien se cubren datos vacios, volumen superior a 120 picks, picks incompletos,
caducados y finalizados, Unicode, tildes, siglas y cambio de dia Madrid.

## C. Diagnostico deportivo honesto

Se conservaron los campos historicos consumidos por cron/admin:

- `status`, `deep_status`, `deep_external_calls`;
- `provider_authenticated`, `provider_plan`, `quota`;
- `capabilities`, `last_sample`.

Se anadieron campos compatibles y explicitos:

- `job_execution`: resultado, intervalo, llamadas y procesados de la ejecucion
  deportiva actual.
- `deep_execution`: si el trabajo profundo corrio, no estaba debido o es
  desconocido.
- `provider_access`: `AUTHENTICATED`, `ACCESS_FAILED` o `NOT_CHECKED`, con fuente
  y momento de la comprobacion cuando existen.
- `provider_plan_observation`: plan observado o `UNKNOWN`; configuracion detectada
  no equivale a plan autenticado.
- `quota_observation`: valor actual solo si procede del deep run actual; una muestra
  historica queda `LAST_OBSERVED_NOT_CURRENT`.
- `coverage`: separa respuesta recibida de escritura de la ejecucion o total del
  almacen. `persisted=5` y `received=0` ya no se presentan como la misma medida.
- `data_freshness`: `NOT_ESTABLISHED` mientras no se evalúen timestamps de cada
  partido, marcador, alineacion o estadistica.

Estados probados: no solicitado, no debido, respuesta vacia valida, fallo de
acceso, cuota limitada, capacidad no disponible, muestra historica y estado
desconocido. Un HTTP 200 o `overall=PASS` sigue significando ejecucion del proceso,
no cobertura deportiva completa.

El payload compacto de la aplicacion y el master runner aceptan los nuevos campos
mediante listas permitidas, limites de longitud, contadores numericos y redaccion
del secreto. Una prueba detecto durante el desarrollo que el campo legacy
`provider_plan` no estaba sanitizado; se corrigio antes del cierre.

## D. QA reproducible

| Control | Resultado |
|---|---|
| Suite exacta del candidato publicable | 437/437 PASS en 56 archivos de test; exit 0; 0 conexiones salientes |
| Tests nuevos de esta reparacion | 10 PASS dentro de la suite exacta |
| `py_compile` | PASS |
| `compileall` | PASS |
| Jinja con entorno Flask real aislado | 199/199 PASS; 0 conexiones salientes |
| Smoke/rutas | 8/8 incluidos en la matriz focal |
| Sports Truth | 27/27 incluidos en la matriz focal |
| Calendario/Madrid Time | 63 + 6 tests incluidos; PASS |
| Privacy + Secret Guard sin generar informe | 1102 archivos; 0 hallazgos; valores no impresos |
| Benchmark autenticado `/app` | 9/9 respuestas HTTP 200; contexto completo |

Incidencias intermedias registradas, no ocultadas:

1. La primera matriz de diagnostico encontro un valor legacy de plan no
   sanitizado. Se corrigio y la regresion queda permanente.
2. Una ejecucion focal inicial activo `NEMESIS_LOCAL_SAFE_MODE`; ese guard bloqueo
   correctamente el endpoint de automatizacion con 403. Se repitio en modo de
   prueba aislado compatible, manteniendo socket saliente bloqueado: 142/142 PASS.
3. Un parseo Jinja generico no conocia el filtro Flask
   `madrid_datetime_label`. La validacion correcta con `app.jinja_env` compilo
   199/199 plantillas.

No ejecutado por limites del encargo:

- navegador o produccion real;
- Render y sus logs;
- proveedores deportivos y `/api/live`;
- Telegram, Stripe o cron reales;
- medicion P95 productiva.

## E. Preservacion y estado de integracion

Hashes finales protegidos:

- `SPORTS_DATA_LIVE_CERTIFICATION.md` DAY 3:
  `BD6FD290282682986F626FB966127F9B56D6310DC970A3DA90207B8D4AFBD642`.
- `NEMESIS_X_IMPLEMENTATION_RULES.md`:
  `ECAFCDC8AE674EBA476D93BB59E9FA3BC00767F673ACE01211A75FCE6CC88FC7`.
- `PRODUCT_PRINCIPLES.md`:
  `7802D0D63FE33458D76B2B6FF9D8BF6FB87D11B07FFC62E9F3E6F02AC1065A80`.
- reglas de trabajo del centro de control:
  `2DE7B71D409F75290528266F081EEF5B48D24256EF7425F1C865CD45CBC0ACDC`.
- `data/runtime/not_found_events.json`:
  `3CB4BF791703CD7FF0507E38CBD4768027721704184505DF023B72DE8C4425B3`.
- informe historico V915:
  `557DCA39950F151B187A7DCCAED812A63FB58078F28490BBF8E1843A0D8E5019`.

Clasificacion final:

- Dashboard runtime: **IMPLEMENTADO LOCALMENTE** y **VALIDADO LOCALMENTE**.
- Diagnostico deportivo: **IMPLEMENTADO LOCALMENTE** y **VALIDADO LOCALMENTE**.
- Match Context previo: conservado; no se reinicio ni se abrio otro motor.
- Candidato exacto de seis rutas: **AISLADO, VALIDADO Y AUTORIZADO PARA PUBLICACION**.
- Desplegado: **NO**.
- Verificado en produccion: **NO**.

## Pendientes concretos

1. Publicar exclusivamente el candidato exacto ya separado, sin incluir Match
   Context ni otros cambios locales.
2. Tras el auto-deploy, observar `/app` autenticado solo si existe una sesion
   autorizada, sin convertir una muestra en P95.
3. Incorporar frescura por entidad al diagnostico solo cuando exista un contrato
   aprobado que preserve procedencia de timestamps; hasta entonces debe seguir
   `NOT_ESTABLISHED`.
