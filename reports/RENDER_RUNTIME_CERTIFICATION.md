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

## Actualizacion LRM-001 External Gates Precheck - 2026-08-02 23:33 Madrid

Modo: GET read-only, sin deploy, sin push, sin ejecuciones.

| Endpoint | Estado | Tiempo | Evidencia |
|---|---:|---:|---|
| `/` | 200 | 2473 ms | Home publica servida. |
| `/api/health` | 200 | 333-650 ms | `ok=true`, `initialized=true`, `db_path_configured=true`. |
| `/api/runtime-version` | 200 | 1364-1910 ms | Version V940, `version_files_match=true`, SHA `ad666b528fff427e09d5e37f3137bb00d45f90c6`. |
| `/version` | 200 | 310-326 ms | App NeMeSiS SHARK PRO, version V940. |
| `/api/cache/status` | 403 | 278 ms | Endpoint protegido; cache status visible por runtime como `available`. |
| `/admin/observability` | 200 | 679-1973 ms | HTML protegido/login; contenido operacional no certificado. |

Observacion: durante el mismo gate hubo lecturas iniciales 502 en endpoints publicos; la repeticion final fue 200. Sin logs Render no se puede explicar ni cerrar esa intermitencia.

Decision Render: PARTIAL operacional. Health/runtime/SHA son PASS en la ultima lectura, pero logs y observabilidad siguen BLOCKED_BY_ACCESS.
