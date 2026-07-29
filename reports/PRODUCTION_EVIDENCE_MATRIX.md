# PRODUCTION EVIDENCE MATRIX

Fecha Madrid: 2026-07-29
Base observada: https://bot-apuestas-crgf.onrender.com
Modo: read-only

| ID | Area | Estado | Evidencia | Endpoint/Fuente | Hora Madrid | Limitaciones |
|---|---|---|---|---|---|---|
| PEM-001 | Health | PASS | HTTP 200, `ok=true`, `initialized=true` | `/api/health` | 22:38:44 | No cubre cron ni pagos |
| PEM-002 | Version publica | PASS | HTTP 200, V940 | `/version` | 22:38:45 | Identidad basica |
| PEM-003 | Runtime | PASS | HTTP 200, V940, `version_files_match=true` | `/api/runtime-version` | 22:38:45 | No cubre logs Render |
| PEM-004 | SHA | PASS | Runtime y GitHub remoto en `21b04563089309a8f73ea9ca22ec929d944e1545` | Runtime + `git ls-remote` | 22:39-22:40 | No hubo push en este gate |
| PEM-005 | DB persistente | PASS | `db_accessible=true`, `/data/database.db`, `db_exists=true` | `/api/runtime-version` | 22:39:13 | Restore no probado |
| PEM-006 | Cron sports | PARTIAL | Last tick reciente, status PARTIAL | `/api/runtime-version` | 22:39:13 | No se ejecuto cron |
| PEM-007 | Master Tick | NOT_RECORDED | `v937_cron_master_status=NOT_RECORDED` | `/api/runtime-version` | 22:39:13 | Bloquea readiness operacional |
| PEM-008 | Telegram config | PARTIAL | Configurado, protegido sin sesion | Runtime + admin API 403 | 22:38-22:39 | Sin envio ni dry-run admin |
| PEM-009 | Stripe test | PARTIAL | Test mode, ready, no real charge | `/api/runtime-version` | 22:39:13 | No checkout/webhook test |
| PEM-010 | Gateway deportivo | PASS | Provider available, cache guard, credit guard, last sync known | `/api/runtime-version` | 22:39:13 | Sin llamadas externas en gate |
| PEM-011 | Observability | BLOCKED_BY_ACCESS | 403 admin requerido | `/api/observability/*` | 22:38:48 | Necesita admin read-only |
| PEM-012 | Logs | BLOCKED_BY_ACCESS | Sin Render logs; observability 403 | Render/observability | 22:38:48 | Necesita acceso Render |
| PEM-013 | Backups | PARTIAL | `data_backup_enabled=false`; Data Vault 403 | Runtime + `/api/admin/data-vault/backups` | 22:38-22:39 | No backup validado |
| PEM-014 | Restore | NOT_RECORDED | No ejecutado por seguridad | No ejecutado | 2026-07-29 | Requiere drill aislado |
| PEM-015 | Variables criticas | PARTIAL | Config masked; no secretos impresos | `/api/runtime-version` | 22:39:13 | Falta Render dashboard/API read-only |
| PEM-016 | Cache | PARTIAL | API cache enabled, CSS busting true; cache API 403 | Runtime + `/api/cache/status` | 22:38-22:39 | Sin vista admin cache |
| PEM-017 | Seguridad admin | PASS | APIs admin devuelven 403 sin sesion | multiples `/api/admin/*` | 22:38-22:39 | No valida contenido admin |
| PEM-018 | Public smoke | PASS | Rutas publicas 200, sin 5xx | `/`, `/calendar`, `/live`, `/picks`, `/shark` | 22:40 | No es Browser QA completo |

## Resumen

PASS: Health, Runtime, SHA, DB persistente observada, Gateway deportivo, seguridad admin, smoke publico.

PARTIAL: Render, Cron, Scheduler, Telegram, Stripe, Backups, Variables, Cache.

NOT_RECORDED: Master Tick, Restore.

BLOCKED_BY_ACCESS: Observability y Logs.
