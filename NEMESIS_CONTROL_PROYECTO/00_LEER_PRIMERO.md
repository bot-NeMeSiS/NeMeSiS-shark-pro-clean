# NeMeSiS Control de Proyecto

## Verdad actual

- Fecha de conciliacion: 2026-09-06 (Europe/Madrid).
- Rama: `main`.
- HEAD local y referencia local de `origin/main`: `8ab59a16b6dd0ae69727547c78709d012b4d3fb7`.
- Ultimo runtime de Render verificado: `6295222a3cd0c77c8ebd3ac8c304017d7b93ca8b`;
  no se ha usado produccion para la reconciliacion CI actual.
- Version declarada: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`.
- Produccion: web y cron quedaron LIVE, con health PASS y runtime alineado con
  `6295222a` en la ultima comprobacion read-only.
- Sports Truth y DAY 3 estan integrados desde `6295222a`; `8ab59a16` solo
  actualiza documentacion de control.
- Incrementos integrados: reparacion de dashboard/diagnostico en `46dbe05d` y Match Context en su hijo `6295222a`.
- Trabajo actual: reconciliacion local de `CI_SPORTS_TRUTH_GATE`. El arbol tiene
  una reparacion acotada en Sports Truth/adapter/tests/check y esta documentacion;
  no hay staging, commit, push, merge, deploy ni repeticion remota de Actions.
- Resultado historico de GitHub para `6295222a`: `qa=SUCCESS`, `smoke=SUCCESS`,
  `preflight=FAILURE` y `certify-production=SKIPPED` (run `34048426812`, job
  `101527550445`). Ese historial no se reescribe por el PASS local posterior.
- Limpieza anterior: `NO_OP_ALREADY_CLEAN`; `RESTAURACION_NO_NECESARIA`.

## Orden de lectura

1. `ESTADO_ACTUAL_PROYECTO.md`
2. `INCIDENCIAS_Y_HALLAZGOS_PRODUCCION.md`
3. `TAREAS_PROGRAMADAS_Y_VIGILANCIA.md`
4. `ROADMAP_Y_PROXIMOS_AVANCES.md`
5. `MAPA_COMPLETO_ECOSISTEMA_NEMESIS.md`
6. `REGLAS_TRABAJO_CHATGPT_CODEX_RELEASES.md`

## Principios que no se negocian

- SPORTS FIRST, SHARK SECOND, BETTING THIRD.
- Un partido solo es LIVE con evidencia confirmada y fresca.
- FT, FINISHED, CANCELLED, POSTPONED, ABANDONED y SUSPENDED nunca son LIVE.
- No se inventan minuto, score, jugadores, alineaciones, cuotas ni metricas.
- Solo relojes de observacion del proveedor (`last_synced_at`,
  `provider_updated_at`, `live_updated_at`) pueden acreditar frescura; un write
  local o `updated_at` generico no rejuvenecen datos.
- No se llama a proveedores durante el render de paginas.
- Cliente y Admin mantienen autorizacion separada.
- Push, deploy, gasto, Telegram real y Stripe live requieren autorizacion expresa.

## Fuentes de verdad

- Codigo/producto: raiz oficial `NeMeSiS shark pro`.
- Estado deportivo: `engines/v935_launch_trust_engine.py`; adaptadores y dominio
  deben delegar en ese contrato, no clasificar en paralelo.
- Hora: `engines/madrid_time_engine.py`.
- Identidad deportiva: contratos canonicos de `app.py` y `engines/sports_domain_model_engine.py`.
- Referencias visuales: solo imagenes oficiales de `REFERENCE_ONLY`; no codigo ni payload historico.
- Produccion: evidencia read-only de Git, Render health/runtime y QA real.
