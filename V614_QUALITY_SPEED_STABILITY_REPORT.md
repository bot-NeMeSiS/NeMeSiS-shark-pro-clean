# V614 Quality, Speed & Stability Report

## Estado

- Versión consolidada: `V614_QUALITY_SPEED_STABILITY`
- Objetivo cubierto en esta pasada: estabilidad defensiva, reducción de trabajo repetido, endurecimiento de `/admin/data-center`, scheduler diferido fuera de login/auth y trazabilidad de entrega.
- Límite del entorno local: no fue posible ejecutar smoke HTTP reales con `Flask.test_client()` porque el runtime disponible en esta sandbox no tiene `flask` instalado.

## Errores hallados y causa

1. Doble tratamiento de errores `500` en `app.py`
- Causa: coexistían un handler legacy y el bloque V607 de observabilidad.
- Riesgo: respuestas inconsistentes, diagnósticos duplicados y mantenimiento frágil.
- Acción: el handler legacy ahora delega en V607.

2. `/admin/data-center` era propenso a caer entero si fallaba una sola métrica
- Causa: el panel llamaba de forma directa a múltiples resúmenes de motores sin envoltura defensiva.
- Riesgo: un fallo parcial en warehouse, learning, Telegram o performance podía tumbar toda la página.
- Acción: se añadieron envoltorios seguros para las métricas del panel.

3. Trabajo repetido en `beta_readiness_summary()` y `data_center_summary()`
- Causa: recomputación frecuente de resúmenes pesados y doble llamada a `scheduler_status()`.
- Riesgo: latencia extra en dashboards y admin pages.
- Acción: caché en memoria con TTL corto y reutilización del estado del scheduler.

4. Arranque diferido del scheduler también podía dispararse desde flujos de autenticación
- Causa: `startup_after_request` solo excluía `/` y endpoints de health.
- Riesgo: login/admin-login con trabajo adicional no relacionado.
- Acción: exclusión explícita de rutas auth y `HEAD`.

## Archivos modificados

- [`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\app.py`](C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\app.py)
- [`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\VERSION.txt`](C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\VERSION.txt)
- [`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\V614_QUALITY_SPEED_STABILITY_DIFF.patch`](C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\V614_QUALITY_SPEED_STABILITY_DIFF.patch)

## Validación ejecutada

- `python -m compileall app.py engines database_manager.py`: OK
- Búsqueda de mojibake real `Ã/Â/â` en `app.py`, `templates/`, `engines/`, `static/`: sin restos detectados tras la pasada

## Métricas antes/después

- `beta_readiness_summary()` antes: sin caché
- `beta_readiness_summary()` después: TTL memoria `30s`
- `data_center_summary()` antes: sin caché y con doble llamada a `scheduler_status()`
- `data_center_summary()` después: TTL memoria `20s` y una sola llamada a `scheduler_status()`
- `startup_after_request()` antes: podía lanzar scheduler tras auth
- `startup_after_request()` después: excluye `/cliente-login`, `/login`, `/entrar`, `/registro`, `/admin-login`, `/admin-bootstrap` y `HEAD`

## Trazabilidad de módulos

| Módulo | Estado | Ruta | Engine | Template/API | Conectado |
|---|---|---|---|---|---|
| SHARK | ACTIVO | `/shark`, `/api/shark/*`, `/shark-core` | `shark_engine`, `shark_intelligence_core` | rutas + APIs | Sí |
| SHARK Learning | ACTIVO | `/api/shark-learning/*` | `shark_learning_engine` | API + admin/data-center | Sí |
| SHARK Accuracy | ACTIVO | `/api/shark-accuracy/*` | `shark_accuracy_engine` | API + admin/data-center | Sí |
| Auto Picks | ACTIVO | `/picks-automaticos`, `/api/autonomous-picks/status` | lógica en `app.py` + scheduler | página + API | Sí |
| Telegram | ACTIVO | `/telegram`, `/api/telegram/*`, `/api/telegram-autonomous/*` | `telegram_*` engines | página + APIs | Sí |
| Warehouse | ACTIVO | `/api/warehouse/*` | `historical_warehouse_engine`, `football_data_warehouse_engine` | API + admin/data-center | Sí |
| API-Football | PARCIAL | vía `football_warehouse`/provider | `football_data_warehouse_engine`, `data_provider_engine` | admin/API | Sí, depende de credenciales |
| The Odds API | ACTIVO | `/api/odds/*`, `/api/odds-value/*` | `odds_value_engine` | APIs + admin/data-center | Sí |
| TheSportsDB | ACTIVO | `/api/sportsdb/*`, `/api/sportsdb-enrichment/*`, highlights | `sportsdb_*` engines | APIs + admin/data-center | Sí |
| Live | ACTIVO | `/live`, `/live-depth`, `/api/live*` | `live_engine` | página + APIs | Sí |
| Calendario | ACTIVO | `/calendar`, `/calendario`, `/api/calendar` | `match_engine`, sync engines | página + API | Sí |
| Picks | ACTIVO | `/picks`, `/api/picks*`, `/admin/picks` | picks logic en `app.py` | páginas + APIs | Sí |
| Match Detail | ACTIVO | `/match/<id>`, `/partido/<id>` | `live_engine` + helpers | página + APIs detalle | Sí |
| Membresías | ACTIVO | `/membresias`, `/membership`, `/api/membership`, `/admin/memberships` | `membership_engine` | páginas + APIs | Sí |
| ROI Dashboard | ACTIVO | `/admin/dashboard`, `/api/performance/*` implícito en panel | `shark_performance_engine` | dashboard/admin | Sí |

## Variables Render recomendadas

- `SECRET_KEY`
- `DB_PATH=/data/database.db`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_USERNAME`
- `BACKGROUND_JOBS_ENABLED=1`
- `BACKGROUND_JOBS_STARTUP=1`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`
- `THE_ODDS_API_KEY`
- `ENABLE_ODDS_API=1`
- `ENABLE_LIVE_API=1`
- `API_FOOTBALL_KEY` si el proveedor está habilitado en producción

## Siguiente validación recomendada en Render

1. Abrir `/api/health`, `/api/runtime-version` y `/api/startup-check`.
2. Probar `/`, `/login`, `/admin-login`, `/picks`, `/live`, `/calendar`, `/admin/data-center`, `/admin/observability`.
3. Confirmar que ningún login dispara trabajo pesado visible.
4. Revisar `X-Response-Time-ms` en `/picks`, `/live`, `/calendar` y `/admin/data-center`.
5. Ejecutar un test de Telegram desde `/api/telegram/send-test`.
