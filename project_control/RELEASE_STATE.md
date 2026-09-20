# Release State

Actualizado 2026-09-20 con GitHub y Render observados.

<!-- releases:start -->
| ID | Tipo | Rama | HEAD | Estado | Evidencia | Limite |
|---|---|---|---|---|---|---|
| MAIN | PRODUCTION_BASE | main | cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0 | LIVE | GitHub PR #16 + Render web/cron | certify-production aun completa ventanas de observacion |
| PR19 | MERGED_RESULTS_READ_PATH | PR #19 | cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0 | MERGED_LIVE | QA/preflight/smoke verdes | fecha pasada usa SQLite read-only; proveedor real no recertificado |
| PR16 | MERGED_CANDIDATE | PR #16 | 2ed82e57ec7d8fd3a5dd92e8d77402ac5cd16610 -> cc6c7dfc | MERGED | QA/Smoke/preflight verdes | no certifica externos por si solo |
| SENTINEL | INTEGRATED_LOCAL_SAFE | main | cc6c7dfc | PRODUCTION_VALIDATION | CI Sentinel/Secret Guard + runner LOCAL SAFE | no executor productivo |
| DIRECTO | INTEGRATED_WITH_GAPS | main | cc6c7dfc | QA | codigo/tests superiores a PR #14 | feed real y browser productivo completo pendientes |
| PR14 | HISTORICAL | chatgpt/directo-canonical-consumer | ef759cb88d46463424342598a765a68a0a057a7a | CLOSED_SUPERSEDED | PR #14 | no fusionar |
| PR15 | HISTORICAL | codex/sentinel-operaciones-local | f533b9c7777fe701a8000a2b8dc32fa5ecce3500 | CLOSED_SUPERSEDED | PR #15 | no fusionar |
| DESIGN | PRESERVE | design branches | historical | NOT_CERTIFIED | project control / referencias | R9/H07/conformidad global pendientes |
<!-- releases:end -->

## Produccion observada

- Web Render LIVE en `cc6c7dfc...`.
- Cron Render LIVE en `cc6c7dfc...`.
- QA y Smoke de push: SUCCESS.
- Preflight productivo: SUCCESS.
- No 5xx/Traceback/ERROR observados en el barrido posterior al deploy.
- Provider profundo, pagos, derechos y hardware real no se heredan como PASS.

## Publicacion futura

Todo siguiente cambio requiere rama/PR, checks del SHA exacto y nueva decision de merge.
No reutilizar automaticamente ramas superseded.


## Follow-up de Resultados 20/09

PR #23 integrado en `cc6c7dfc...`: paridad página/API, Finalizados date-scoped y provider-state coherente. Render web/cron LIVE. No certifica cobertura del proveedor ni derechos externos.


## Sports Reality PR #26

Integrado en `cc6c7dfc...`; Render web/cron LIVE. QA/preflight/Smoke del candidato exacto fueron SUCCESS. Pendiente primera observacion de cron posterior al deploy para clasificar la fuente REAL actual.
