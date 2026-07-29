# RENDER RUNTIME CERTIFICATION

Fecha Madrid: 2026-07-29
Base observada: https://bot-apuestas-crgf.onrender.com
Modo: read-only

## Runtime identity

| Campo | Valor |
|---|---|
| Runtime version | `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL` |
| VERSION.txt | `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL` |
| APP_VERSION | `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL` |
| Version files match | true |
| Deployment alignment | `aligned_local_files` |
| Runtime path | `/opt/render/project/src/app.py` |
| Service worker cache | `NEMESIS_CACHE_V940` |
| Static CSS cache busting | true |
| Runtime SHA hint | `21b04563089309a8f73ea9ca22ec929d944e1545` |
| GitHub remote main | `21b04563089309a8f73ea9ca22ec929d944e1545` |

## Render and storage

| Control | Estado | Evidencia |
|---|---|---|
| Web service reachable | PASS | `/api/health` 200 |
| DB path | PASS | `/data/database.db` |
| DB accessible | PASS | `db_accessible=true` |
| DB exists | PASS | `render.db_exists=true` |
| Persistent disk inferred | PASS | DB under `/data` and accessible |
| Render logs | BLOCKED_BY_ACCESS | No Render dashboard/API log access in this gate |
| Render variables | PARTIAL | Runtime masked presence only; no dashboard verification |

## Critical variable evidence

| Variable area | Estado | Runtime evidence |
|---|---|---|
| Automation secret | PASS | configured, masked |
| Telegram bot/channel | PARTIAL | configured, no delivery test |
| API Sports | PASS | configured, provider available, credit guard enabled |
| The Odds | PARTIAL | configured, but odds data quality shows stale/invalid historical counters |
| Stripe | PARTIAL | test mode ready, no checkout/webhook proof in this gate |
| Render API key | PARTIAL | runtime indicates missing; may only affect deploy automation, not serving app |
| Data backup | PARTIAL | disabled |

## Decision

RENDER RUNTIME: PASS for live service identity, health, SHA alignment and DB accessibility.

RENDER OPERATIONS: PARTIAL because Render logs, dashboard variables, cron execution history and backups were not accessible as read-only evidence in this gate.
