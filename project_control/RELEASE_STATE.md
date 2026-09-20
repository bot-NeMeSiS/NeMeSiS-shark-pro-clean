# Release State

Actualizado 2026-09-20 con GitHub y Render observados.

<!-- releases:start -->
| ID | Tipo | Rama/Ref | HEAD | Estado | Evidencia | Limite |
|---|---|---|---|---|---|---|
| MAIN | PRODUCTION_BASE | main | 7a1ba50bf9d6fec8648fcacc2dae72b7cbe730ba | LIVE | GitHub PR #16 + Render web/cron | certify-production aun completa ventanas de observacion |
| PR16 | MERGED_CANDIDATE | PR #16 | 2ed82e57ec7d8fd3a5dd92e8d77402ac5cd16610 -> 7a1ba50b | MERGED | QA/Smoke/preflight verdes | no certifica externos por si solo |
| SENTINEL | INTEGRATED_LOCAL_SAFE | main | 7a1ba50b | PRODUCTION_VALIDATION | CI Sentinel/Secret Guard + runner LOCAL SAFE | no executor productivo |
| DIRECTO | INTEGRATED_WITH_GAPS | main | 7a1ba50b | QA | codigo/tests superiores a PR #14 | feed real y browser productivo completo pendientes |
| PR14 | HISTORICAL | chatgpt/directo-canonical-consumer | ef759cb88d46463424342598a765a68a0a057a7a | CLOSED_SUPERSEDED | PR #14 | no fusionar |
| PR15 | HISTORICAL | codex/sentinel-operaciones-local | f533b9c7777fe701a8000a2b8dc32fa5ecce3500 | CLOSED_SUPERSEDED | PR #15 | no fusionar |
| DESIGN | PRESERVE | design branches | historical | NOT_CERTIFIED | project control / referencias | R9/H07/conformidad global pendientes |
<!-- releases:end -->

## Produccion observada

- Web Render LIVE en `7a1ba50b...`.
- Cron Render LIVE en `7a1ba50b...`.
- QA y Smoke de push: SUCCESS.
- Preflight productivo: SUCCESS.
- No 5xx/Traceback/ERROR observados en el barrido posterior al deploy.
- Provider profundo, pagos, derechos y hardware real no se heredan como PASS.

## Publicacion futura

Todo siguiente cambio requiere rama/PR, checks del SHA exacto y nueva decision de merge.
No reutilizar automaticamente ramas superseded.
