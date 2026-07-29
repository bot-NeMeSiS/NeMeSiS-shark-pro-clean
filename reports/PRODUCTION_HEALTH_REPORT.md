# PRODUCTION HEALTH REPORT

Fecha Madrid: 2026-07-29
Base observada: https://bot-apuestas-crgf.onrender.com
Produccion modificada: false

## Health endpoints

| Endpoint | Estado | Tiempo | Evidencia | Decision |
|---|---:|---:|---|---|
| `/api/health` | 200 | 564 ms | `ok=true`, `initialized=true`, `db_path_configured=true`, version V940 | PASS |
| `/version` | 200 | 450 ms | `ok=true`, app NeMeSiS SHARK PRO, version V940 | PASS |
| `/api/runtime-version` | 200 | 2583 ms | V940, archivos de version alineados, SHA reportado | PASS |

## Public smoke

No se observaron respuestas 5xx en las rutas publicas revisadas.

| Ruta | Estado observado | Decision |
|---|---:|---|
| `/` | 200 | PASS |
| `/calendar` | 200 | PASS |
| `/live` | 200 | PASS |
| `/picks` | 200 | PASS |
| `/track-record` | 200 | PASS |
| `/shark` | 200 | PASS |
| `/telegram` | 200 tras login redirect | PASS protegido |
| `/memberships` | 200 | PASS con latencia a observar |
| `/admin-login` | 200 | PASS |
| `/admin/dashboard` | 200 tras login redirect | PASS protegido |
| `/admin/operations-center` | 200 tras login redirect | PASS protegido |
| `/admin/founder-dashboard` | 200 tras login redirect | PASS protegido |

## Hallazgos

- La aplicacion esta inicializada y sirve V940.
- La persistencia esta configurada y accesible segun runtime.
- No se detectaron 5xx en la muestra read-only.
- `/memberships` tardo 6204 ms en una observacion aislada; se recomienda repetir medicion antes de declarar excelencia de rendimiento.

## Decision

PRODUCTION HEALTH: PASS para disponibilidad basica y rutas publicas.

No equivale a WORLD CLASS RELEASE READY porque no certifica cron, logs, backup/restore, Telegram ni Stripe.
