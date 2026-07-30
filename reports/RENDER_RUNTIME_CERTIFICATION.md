# RENDER RUNTIME CERTIFICATION

Fecha Madrid: 2026-07-29
Actualizacion Gate 2C: 23:35 Madrid
Base observada: https://bot-apuestas-crgf.onrender.com
Modo: read-only
Produccion modificada: false

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
| Runtime SHA hint | `32211fa153738ac7641c22a73a9ead08b1b1991d` |
| Local HEAD | `32211fa153738ac7641c22a73a9ead08b1b1991d` |
| origin/main | `32211fa153738ac7641c22a73a9ead08b1b1991d` |

## Render and storage

| Control | Estado | Evidencia |
|---|---|---|
| Web service reachable | PASS | `/api/health` 200, `ok=true`, `initialized=true` a las 23:35:00 |
| Runtime reachable | PASS | `/api/runtime-version` 200 a las 23:34:59 |
| DB path | PASS | `/data/database.db` |
| DB accessible | PASS | `db_accessible=true` |
| DB exists | PASS | `render.db_exists=true` |
| Persistent disk inferred | PASS | DB bajo `/data` y accesible |
| Render logs | BLOCKED_BY_ACCESS | No Render dashboard/API log access in this gate |
| Render variables | PARTIAL | Runtime masked presence only; no dashboard verification |

## Critical variable evidence

| Variable area | Estado | Runtime evidence |
|---|---|---|
| Automation secret | PASS | configured, masked |
| Telegram bot/channel | PARTIAL | configured, no delivery test |
| API Sports | PASS | configured, provider available, credit guard enabled |
| The Odds | PARTIAL | configured, but no fresh odds certification in this gate |
| Stripe | PARTIAL | test mode ready, no checkout/webhook proof in this gate |
| Render API key | PARTIAL | runtime indicates missing; affects deploy automation, not current serving app |
| Deploy hook | PARTIAL | runtime indicates missing; affects deployment automation only |
| Data backup | PARTIAL | disabled because `DATA_BACKUP_ENABLED` is absent/not active |

## Cache

CACHE: PASS

Evidence: `service_worker_cache_name=NEMESIS_CACHE_V940`, `api_sports_cache_enabled=true`, `v934_cache_status=available`, and `/api/cache/status` returns 403 without admin session. This certifies namespace/version/basic integrity and protected access. It does not expose internal cache rows.

## Decision

RENDER RUNTIME: PASS for live service identity, health, SHA alignment and DB accessibility.

RENDER OPERATIONS: PARTIAL because Render logs, dashboard variables, cron execution history and automatic backups are not certified with read-only production evidence.
