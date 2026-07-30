# PRODUCTION EVIDENCE MATRIX

Fecha Madrid: 2026-07-29
Actualizacion Gate 2C: 23:35 Madrid
Base observada: https://bot-apuestas-crgf.onrender.com
Modo: read-only
Produccion modificada: false

| ID | Area | Estado | Evidencia | Endpoint/Fuente | Hora Madrid | Limitaciones |
|---|---|---|---|---|---|---|
| PEM-001 | Health | PASS | HTTP 200, `ok=true`, `initialized=true`, `db_path_configured=true` | `/api/health` | 23:35:00 | Se observo una lectura transitoria previa con `initialized=false`; lectura repetida vuelve a PASS. No cubre cron ni pagos. |
| PEM-002 | Version publica | PASS | HTTP 200, V940 | `/version` | 23:31:52 | Identidad basica. |
| PEM-003 | Runtime | PASS | HTTP 200, V940, `version_files_match=true` | `/api/runtime-version` | 23:34:59 | No cubre logs Render. |
| PEM-004 | SHA | PASS | Runtime, local HEAD y `origin/main` en `32211fa153738ac7641c22a73a9ead08b1b1991d` | Runtime + Git local | 23:34-23:35 | No hubo push en este gate. |
| PEM-005 | DB persistente | PASS | `db_accessible=true`, `/data/database.db`, `render.db_exists=true` | `/api/runtime-version` | 23:34:59 | Restore productivo no probado. |
| PEM-006 | Cron sports | PARTIAL | Last tick reciente `2026-07-29T23:32:01+02:00`, age 178s, status `PARTIAL` | `/api/runtime-version` | 23:34:59 | No se ejecuto cron; faltan logs Render. |
| PEM-007 | Master Tick | NOT_RECORDED | `v937_cron_master_status=NOT_RECORDED`, `runtime_stability.last_master_tick={}` | `/api/runtime-version` | 23:34:59 | Bloquea readiness operacional. |
| PEM-008 | Telegram config | PARTIAL | Configurado; prueba real no ejecutada | Runtime | 23:34:59 | Sin envio ni dry-run admin autorizado. |
| PEM-009 | Stripe test | PARTIAL | Test mode; prueba real no ejecutada | `/api/runtime-version` | 23:34:59 | No checkout/webhook test. |
| PEM-010 | Gateway deportivo | PASS | Provider available, cache guard, credit guard, last sync known | `/api/runtime-version` | 23:34:59 | Sin llamadas externas en gate. |
| PEM-011 | Observability | BLOCKED_BY_ACCESS | Endpoints admin read-only devuelven 403 sin sesion | `/api/observability/*` | 23:35 | Necesita admin read-only. |
| PEM-012 | Logs | BLOCKED_BY_ACCESS | Sin Render logs; observability admin 403 | Render/observability | 23:35 | Necesita acceso Render. |
| PEM-013 | Backups | PARTIAL | `data_backup_enabled=false`; causa: `DATA_BACKUP_ENABLED` ausente/no activo, safe default false | Runtime + codigo local | 23:34:59 | No backup productivo validado. |
| PEM-014 | Restore | PARTIAL | Drill local aislado PASS con DB temporal, backup sha256 y copia restaurada; DB real no tocada | QA local aislada | 23:34 | No certifica restore productivo. |
| PEM-015 | Variables criticas | PARTIAL | Presencia/estado enmascarados: automation secret configured, Telegram configured, Sports APIs configured; Render API key/deploy hook missing; backup disabled | `/api/runtime-version` | 23:34:59 | Falta Render dashboard/API read-only para inventario completo. |
| PEM-016 | Cache | PASS | `service_worker_cache_name=NEMESIS_CACHE_V940`, `api_sports_cache_enabled=true`, `v934_cache_status=available`; `/api/cache/status` protegido 403 | Runtime + cache endpoint | 23:34-23:35 | No lista items internos sin sesion admin. |
| PEM-017 | Seguridad admin | PASS | APIs admin devuelven 403 sin sesion | multiples `/api/admin/*` | 23:35 | No valida contenido admin. |
| PEM-018 | Public smoke | PASS | Rutas publicas sin 5xx en Gate 2 previo; health actual PASS | rutas publicas + `/api/health` | 22:40, 23:35 | No es Browser QA completo. |

## Cambios de estado Gate 2C

- Cache pasa de PARTIAL a PASS por evidencia suficiente de namespace, version, integridad basica y proteccion de listado interno.
- Restore pasa de NOT_RECORDED a PARTIAL por drill local aislado y reversible. No es PASS de produccion.
- Backup queda explicado: `DATA_BACKUP_ENABLED` no esta activo; se clasifica como variable ausente/pendiente de activar, no como backup operativo.
- Cron queda PARTIAL: hay evidencia reciente, pero falta Master Tick/logs Render.

## Resumen Gate 2C

PASS: Health, Version publica, Runtime, SHA, DB persistente observada, Gateway deportivo, Cache, Seguridad admin, Public smoke.

PARTIAL: Render operations, Cron, Scheduler, Telegram, Stripe, Backups, Restore, Variables criticas.

NOT_RECORDED: Master Tick.

BLOCKED_BY_ACCESS: Observability y Logs.
