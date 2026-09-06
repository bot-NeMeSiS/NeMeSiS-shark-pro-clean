# NeMeSiS Control de Proyecto

## Verdad actual

- Fecha de conciliacion: 2026-09-06 (Europe/Madrid).
- Rama: `main`.
- Base local, GitHub y Render verificada: `6295222a3cd0c77c8ebd3ac8c304017d7b93ca8b`.
- Version declarada: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`.
- Produccion: web y cron LIVE; health PASS y runtime alineado con `6295222a` mediante consultas read-only.
- Sports Truth y DAY 3 ya estan integrados en esa base.
- Incrementos integrados: reparacion de dashboard/diagnostico en `46dbe05d` y Match Context en su hijo `6295222a`.
- Trabajo actual: validacion de integracion; solo documentacion local sin commit, push o deploy.
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
