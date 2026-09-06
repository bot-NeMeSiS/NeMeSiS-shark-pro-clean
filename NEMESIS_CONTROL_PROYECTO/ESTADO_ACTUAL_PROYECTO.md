# Estado Actual del Proyecto

Reconstruccion iniciada el 2026-09-05 y cierre QA el 2026-09-06
(Europe/Madrid).

## Resumen ejecutivo

La base publicada permanece alineada en
`fddbeea3b1205e2f05e62bcf95630a7a4c85a4cd`: `main`, `origin/main` y el
runtime de Render observado sirven ese mismo commit. `VERSION.txt`,
`APP_VERSION` y `app.py` conservan
`V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`.

Sobre esa base existe un candidato Sports Truth exclusivamente local y sin
commit. El candidato preserva el trabajo previo y cierra la procedencia del
reloj LIVE desde proveedor hasta DB, adaptadores y superficies: un write de DB,
una lectura de cache o `updated_at` generico ya no rejuvenecen evidencia. Los
estados terminales y suspendidos ganan frente a una senal LIVE contradictoria;
un estado ausente tras kickoff queda `RESULT_PENDING`, nunca FT inferido; score
parcial no inventa cero y ningun minuto se deduce del horario.

El candidato esta respaldado fuera del release mediante copia selectiva,
patch y manifiesto SHA-256. No se copio la DB, el workspace completo, secretos,
logs ni cache.

## Matriz

| Area | Produccion | Local actual | Evidencia / limite |
|---|---|---|---|
| Git / runtime | PASS | CANDIDATO SIN COMMIT | Base `fddbeea3`; no se ha publicado nada |
| Health | PASS | N/A | `/api/health`, `/api/runtime-version` y `/version`, solo lectura |
| Sports Truth | HOTFIX PUBLICADO | PASS LOCAL | Un contrato `MATCH-STATUS-TRUTH-V2`; reloj de proveedor explicito |
| Home / Live / Partidos | PASS conocido | PASS POR CONTRATO/TEST | Sin llamadas nuevas a proveedor; `/api/live` se excluyo del smoke por poder sincronizar |
| Calendario | PASS conocido | PASS LOCAL | Badge legacy no restaura LIVE stale; Browser QA de shell/empty 4/4 |
| Match Center | IMPLEMENTADO | PASS LOCAL | V944 preservada; Browser QA ready/partial 6/6, desktop/tablet/mobile |
| Admin / Founder | IMPLEMENTADO | PASS LOCAL AISLADO | Sesion admin firmada, SQLite temporal, 9/9 cargas Browser QA |
| SHARK / Picks / Telegram | IMPLEMENTADO | PRESERVADO | Consumen estado fail-closed; cero envios iniciados en esta fase |
| Stripe / membresias | LIVE BLOQUEADO | SIN CAMBIOS | Cero cobros o cambios de precio iniciados |
| Continuous Evolution | ACTIVE OBSERVADO | SIN CAMBIOS | Master tick read-only observado; politica no modificada |
| Visual | NO REAUDITADO | SIN CAMBIOS | No se declara fidelidad visual sin comparacion fisica completa |
| Sports 3-7 dias | EN CURSO | NO ALTERADO | No se inventa DAY ni LIVE Tier S/A |

## Cambios funcionales del candidato

- `app.py`: persiste `last_synced_at`; conversion SportsDB pura por defecto;
  score completo o ausente; confianza stale/unknown/conflict fail-closed.
- `engines/api_football_live_tracker_engine.py`: observacion explicita hasta la
  tabla de matches; estado ausente queda UNKNOWN; SUSP/INT no son LIVE.
- `engines/v935_launch_trust_engine.py`: verdad central de lifecycle y frescura;
  reloj futuro anomalo, stale y contradicciones degradan de forma segura.
- `engines/v934_realtime_sports_engine.py` y
  `engines/live_match_experience_engine.py`: adaptadores delegados a la misma
  verdad y sin score/minuto inventado.
- `engines/sports_domain_model_engine.py`: dominio delegado al contrato central,
  puro, sin red ni DB.
- Adaptadores de Match/Live y tests historicos: estados
  `SUSPENDED`/`RESULT_PENDING` coherentes y fixtures con reloj explicito.
- `tests/test_sports_truth_single_source.py`: 27 regresiones permanentes para
  procedencia, contradicciones, score cero real, estados y consistencia.

## Proveedores y salud observada

- Web Render: LIVE; disco `/data`; DB declarada `/data/database.db`.
- `telegram-auto-tick`: activo, comando
  `python tools/render_cron_master_tick.py`, cadencia observada cada cinco
  minutos; no se modifico.
- Master runner: PASS en la muestra. Esto acredita ejecucion del job, no
  cobertura deportiva.
- Sports pipeline: PARTIAL; `provider_authenticated=false`, plan
  `INACCESSIBLE`, deep calls 0. El ultimo estado tambien registraba limite
  diario del proveedor.
- `api_sports_provider_available=true` solo acredita configuracion/habilitacion.
- Acciones nuevas con coste iniciadas en esta sesion: ninguna. Facturacion y
  coste corriente no fueron auditados, por lo que no se declara un importe.

## QA reproducible

- Pytest completo: 427/427 PASS.
- Sports Truth focal: 27/27 PASS.
- Matriz Sports Truth/Calendario/Dominio/Knowledge/Temporal/P1: 118/118 PASS.
- `py_compile` focal: PASS.
- `compileall` de `app.py`, `engines`, `tests` y `tools`: PASS, pycache fuera del repo.
- Jinja: 199/199 PASS; primer intento tuvo un error de quoting del comando,
  corregido sin fallo de producto.
- Imports/rutas/static: 744 rutas GET, 151 referencias literales de template,
  0 templates o assets ausentes.
- Auditoria route/link: 807 reglas, 21 enlaces directos API/admin clasificados
  como deuda de presentacion, 0 `href` vacios, 0 `javascript:void`, 0 smoke inseguro.
- Smoke Flask: 28/28 PASS; `/api/live` excluido porque puede consumir proveedor.
- Madrid Time: 2/2 PASS.
- Browser Match Center: 6/6 PASS; 13 componentes, 0 overflow, 0 JS, 0 5xx,
  0 peticiones externas/proveedor.
- Browser Calendario: 4/4 PASS en shell, busqueda y empty state; DB temporal
  vacia, por lo que no certifica interaccion con cards reales.
- Browser Founder/Admin: 9/9 PASS con sesion firmada y DB temporal; 0 JS,
  0 peticiones externas.
- Privacy/Secret Guard: 1.102 archivos, 0 secretos confirmados, 0 hallazgos de privacidad.
- Sentinel estatico: 39 rutas criticas, 1.089 enlaces, 0 issues, score 10/10.
- Rendimiento V935: PASS; rutas aisladas respondieron 200.
- `git diff --check`: PASS antes de la conciliacion documental; debe repetirse
  en la revision final del candidato.

## Limites pendientes

- El PASS es local; produccion sigue en `fddbeea3`.
- No hubo partido Tier S/A LIVE real en esta ejecucion ni llamadas de proveedor.
- V946 permanece bloqueada: no se recupero una especificacion original.
- No se hizo una auditoria visual completa ni de toda la aplicacion cliente.
- `/api/live` mantiene un contrato de lectura que puede activar sincronizacion;
  queda separado del candidato y no se uso para observar repetidamente.
- Veintiun enlaces directos a API/admin son deuda de presentacion, no una fuga
  de autorizacion demostrada.

## Publicacion

Commit: NO. Push: NO. Merge PR: NO. Deploy: NO. Render writes: NO.
La siguiente decision requiere revision del diff y autorizacion expresa.
