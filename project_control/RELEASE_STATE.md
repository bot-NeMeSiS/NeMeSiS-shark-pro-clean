# Release State

## Estado remoto vigente · 2026-09-23

| ID | Tipo | SHA | Estado | Evidencia | Límite |
|---|---|---|---|---|---|
| MAIN_REMOTE | PRODUCTION | 228369d42447f37f3023a7f09216205057e4655c | LIVE_WEB_CRON | Render Web/Cron exact-SHA; PR #82 QA/Preflight/Smoke SUCCESS | Guard post-merge programado puede seguir en observación; consultar run actual |
| PR78 | MERGED | 1e2b9d92bb4e61ffab39164f1f46b1fd3f756c01 | DELIVERED | Provider health read-only, 0 llamadas al render | Pago/acceso directo no inferidos |
| PR80 | MERGED | 76e0ba1e53b10384c5af1bc32d19529e382adb00 | DELIVERED | PWA easy install, QA/Preflight/Smoke + Render exact-SHA | iPhone/Android/PC físico NO_VERIFICADO |
| PR82 | MERGED | 228369d42447f37f3023a7f09216205057e4655c | LIVE | Direct check admin+CSRF, cooldown, evidencia saneada | Ninguna llamada real de proveedor ejecutada en esta entrega |
| SENTINEL | INTERNAL_CONTROL | current main | PASS_LOCAL_SAFE | Fresh-process HTTP/browser boundary tests in every Smoke | Executor productivo deshabilitado por diseño; no REAL_PRODUCTION |
| NEXT | ACTIVE_CONTROL | — | HYGIENE_RECONCILIATION | project_control/ACTIVE_WORK.md | No borrar evidencia/ramas; extraer trabajo único antes de cerrar PRs |

El candidato acumulado del 19/09 sigue preservado como procedencia y no se considera
publicado como unidad. Los bloques posteriores son integraciones selectivas contra main.


## Estado remoto vigente · 2026-09-20

| ID | Tipo | SHA | Estado | Evidencia | Límite |
|---|---|---|---|---|---|
| MAIN_REMOTE | PRODUCTION | c7237c4669f7f5c5e0ceefe4150fd71039b49507 | LIVE_WEB_CRON | Render exact-SHA + PR #52 QA/preflight/Smoke | La observación +3600s del guard puede seguir en curso |
| PR51 | MERGED | 1d6afbe7034edb5f63ae1c990edcc807a200c535 | SUPERSEDED_BY_MAIN | fail-fast Odds; post-deploy cron PASS | 429 real post-merge no observado porque Odds usó caché |
| PR52 | MERGED | c7237c4669f7f5c5e0ceefe4150fd71039b49507 | LIVE | Founder Sports freshness, 0 provider calls | Admin visual requiere sesión; CI Browser gate sí pasó |
| NEXT | ACTIVE_BRANCH | — | STALE_EVIDENCE | 3 STALE observados en muestra 200 | No merge hasta QA + preflight + Smoke |

Publicación actual: GitHub `main` despliega automáticamente a Render. No usar hook
o deploy manual mientras Auto Deploy funcione. El snapshot local del 2026-09-19
que sigue debajo queda preservado como histórico y sus frases
`Produccion NOT_TESTED` / `SAFE_TO_PUBLISH=NO` no describen el remoto actual.

## Snapshot local histórico · 2026-09-19


Observado localmente 2026-09-19. No consulta productiva ni nueva consulta remota.
HEAD no incluye cambios sin commit. Una huella de prueba no certifica el arbol posterior.
Estado de candidato no es estado de la cola ni permiso de publicacion.

<!-- releases:start -->
| ID | Tipo | Rama | HEAD | Estado | Evidencia | Limite |
|---|---|---|---|---|---|---|
| MAIN | BASE_LOCAL | main | c4a81003de1b5ccdb3036831583e9c1eb65e4417 | CLEAN_OBSERVED | project_control/CURRENT_TRUTH.md | Coincide con origin/main local; runtime actual NOT_TESTED |
| SENTINEL | CANDIDATE | codex/sentinel-operaciones-local | c4a81003de1b5ccdb3036831583e9c1eb65e4417 | LOCAL_UNCOMMITTED | reports/LOCAL_CONTINUITY_20260919.md | Huella 8e3475faa5665654...; 380 casos distintos verificados, 45 vistas; replay final local; no certificacion global/productiva |
| DESIGN | PRESERVE | codex/cx-design-02 | 317ac8c37c3c74f39b736a207f55079c7d454856 | DIRTY_PRESERVED | reports/LOCAL_CONTINUITY_20260919.md | 4401 registros; no ejecutar app incompleta ni restaurar |
| VISUAL | PRESERVE | codex/design-02-conformance | 7202c1886aec7fee03267b1a709313804360592a | COMMITTED_PRESERVED | project_control/CONVERSATION_INDEX.md | 23 rutas del candidato historico, no copia automatica |
| DOCS | PRESERVE | docs/project-control-20260904 | ad297cf56b7ab302a86b16ae261634549c5a68a4 | DIRTY_PRESERVED | project_control/CONVERSATION_INDEX.md | 6131 registros; no cerrar PR7 ni retirar este worktree aqui |
| PR14 | HISTORICAL_REMOTE_OBSERVATION | PR14 | ef759cb88d46463424342598a765a68a0a057a7a | DRAFT_LAST_OBSERVED | reports/LOCAL_CONTINUITY_20260919.md | Adaptacion local selectiva, no merge; PR12 y parche unificado separados |
<!-- releases:end -->

## Registro de worktrees y ramas

Rutas exactas, HEAD, dirty, relacion main y dependencias en
data/local_dev/organization-20260919/inventory.json; generado con Git de lectura.
Cuatro worktrees registrados; main y Sentinel ACTIVE, Design y documental PRESERVE.
Siete ramas locales: main, codex/sentinel-operaciones-local, codex/cx-design-02,
docs/project-control-20260904, codex/design-02-conformance,
codex/app-icon-identity y backup/production-stable.
Las ultimas cinco conservan commits fuera de main o dependencias; ninguna se borra.
SAFE_TO_RETIRE = 0 verificado; no inferir que squash/merge equivale a ausencia de trabajo unico.

## Publicacion

NO staging / commit / push / PR / merge / deploy. Produccion NOT_TESTED.
SAFE_TO_PUBLISH = NO. Preview/replay no cambian estos limites.
No actualizacion de Render, cron, proveedores, DB real, Telegram o Stripe.
