# Auditoria de variables de entorno

Fecha: 2026-06-02

Alcance real revisado:
- Codigo Python: `app.py`, `database_manager.py`, `engines/*.py`.
- Configuracion: `render.yaml`, `.env.example`, `env.example`.
- Documentacion usada solo para detectar variables historicas, no como uso real de codigo.

Nota importante: no se han leido variables reales de Render, solo referencias existentes en el repositorio. Por eso "nunca utilizadas" significa: aparecen en ejemplos/docs del repo, pero no se leen en el codigo actual.

## Variables usadas realmente en codigo

| Variable | Archivo:linea | Uso |
|---|---|---|
| `ADMIN_EMAIL` | `app.py:4727`, `app.py:4840`, `app.py:6185`, `app.py:6204` | Bootstrap/login admin |
| `ADMIN_NAME` | `app.py:4730`, `app.py:4852`, `app.py:6207` | Nombre admin por defecto |
| `ADMIN_PASSWORD` | `app.py:4729`, `app.py:4842`, `app.py:6185`, `app.py:6206` | Bootstrap/login admin |
| `ADMIN_USERNAME` | `app.py:4728`, `app.py:4841`, `app.py:4851`, `app.py:6205` | Usuario admin por defecto |
| `AUTONOMOUS_CRON_TOKEN` | `app.py:8579`, `app.py:8616` | Token para endpoints cron autonomos |
| `AUTO_GENERATE_PICKS` | `app.py:2323` | Activa generacion automatica de picks |
| `AUTO_PICKS_MIN_SCORE` | `app.py:2325` | Alias legacy para score minimo autopilot |
| `AUTO_PICKS_REFRESH_MINUTES` | `engines/scheduler_engine.py:15` | Intervalo scheduler auto picks |
| `AUTO_SEND_TELEGRAM_PICKS` | `app.py:2324` | Activa envio automatico a Telegram |
| `AUTO_SYNC_ON_STARTUP` | `engines/scheduler_engine.py:56` | Ejecutar scheduler al arrancar |
| `CREST_SYNC_HOURS` | `engines/scheduler_engine.py:11` | Intervalo sync escudos/equipos |
| `DB_PATH` | `app.py:69` | Ruta SQLite |
| `ENABLE_AUTO_SYNC` | `engines/scheduler_engine.py:55` | Activa scheduler interno |
| `ENABLE_LIVE_API` | `app.py:1260`, `app.py:2890` | Permite live API |
| `ENABLE_ODDS_API` | `app.py:1264` | Permite The Odds API |
| `ENABLE_TELEGRAM_AUTO` | `app.py:5130` | Campo legacy de diagnostico Telegram |
| `FLASK_DEBUG` | `app.py:8637` | Debug local en `app.run` |
| `FLASK_SECRET_KEY` | `app.py:73` | Alias de `SECRET_KEY` |
| `LIVE_ALERTS_REFRESH_MINUTES` | `engines/scheduler_engine.py:16` | Intervalo alertas live |
| `LIVE_CACHE_MINUTES` | `app.py:2300`, `engines/scheduler_engine.py:13` | Cache/intervalo live |
| `MAX_AUTO_PICKS_PER_DAY` | `app.py:2326` | Maximo diario autopilot |
| `MIN_SHARK_SCORE_FOR_AUTO_SEND` | `app.py:2325` | Score minimo autopilot |
| `ODDS_CACHE_MINUTES` | `app.py:1268`, `engines/scheduler_engine.py:12` | Cache/intervalo cuotas |
| `ODDS_MARKETS` | `app.py:2765`, `app.py:2834` | Mercados Odds API |
| `ODDS_REGIONS` | `app.py:2764`, `app.py:2833` | Regiones Odds API |
| `POPULATION_WARMUP_HOURS` | `app.py:2189` | Cadencia warmup de poblacion |
| `POPULATION_WARMUP_LIMIT` | `app.py:2565`, `app.py:2644` | Limite warmup/scheduler |
| `PORT` | `app.py:8637` | Puerto local; Render lo inyecta |
| `RECOMMENDATIONS_REFRESH_MINUTES` | `engines/scheduler_engine.py:14` | Intervalo recomendaciones |
| `SCHEDULER_LOG_CLEANUP_HOURS` | `engines/scheduler_engine.py:18` | Intervalo limpieza scheduler |
| `SCHEDULER_LOG_MAX_ROWS` | `app.py:2603` | Maximo logs internos |
| `SECRET_KEY` | `app.py:73` | Clave de sesiones Flask |
| `SPORTSDB_SYNC_HOURS` | `engines/scheduler_engine.py:10` | Intervalo calendario SportsDB |
| `SQLITE_BUSY_TIMEOUT_MS` | `database_manager.py:12` | Busy timeout SQLite |
| `SQLITE_RETRY_ATTEMPTS` | `database_manager.py:13` | Reintentos SQLite |
| `SQLITE_RETRY_BASE_SLEEP` | `database_manager.py:14` | Pausa base SQLite |
| `SQLITE_TIMEOUT_SECONDS` | `database_manager.py:11` | Timeout conexion SQLite |
| `STRIPE_PRICE_ELITE` | `engines/subscription_control_engine.py:234`, `engines/subscription_control_engine.py:238`, `engines/subscription_control_engine.py:268` | Readiness de Stripe futuro |
| `STRIPE_PRICE_PRO` | `engines/subscription_control_engine.py:234`, `engines/subscription_control_engine.py:238`, `engines/subscription_control_engine.py:268` | Readiness de Stripe futuro |
| `STRIPE_SECRET_KEY` | `engines/subscription_control_engine.py:234`, `engines/subscription_control_engine.py:238`, `engines/subscription_control_engine.py:268` | Readiness de Stripe futuro |
| `TELEGRAM_AUTO_MINUTES` | `app.py:5131` | Campo legacy de diagnostico Telegram |
| `TELEGRAM_AUTO_SEND_WINDOW_HOURS` | `app.py:2327` | Ventana autopilot Telegram |
| `TELEGRAM_BOT_TOKEN` | `app.py:5113`, `app.py:5458`, `app.py:5542`, `app.py:5543`, `app.py:5884` | Token Bot API Telegram |
| `TELEGRAM_CHAT_ID` | `app.py:2504`, `app.py:5004`, `app.py:5114`, `app.py:5209`, `app.py:5341`, `app.py:5406`, `app.py:5497`, `app.py:5544`, `app.py:5545`, `app.py:5679`, `app.py:5885`, `app.py:6344`, `app.py:6346`, `app.py:6352`, `app.py:6354`, `app.py:6385`, `app.py:6432`, `app.py:7217`, `app.py:7231`, `app.py:7354`, `app.py:7373`, `app.py:7382`, `app.py:7400` | Destino global Telegram |
| `TELEGRAM_PREPARE_HOURS` | `engines/scheduler_engine.py:19` | Intervalo tarea Telegram |
| `THE_ODDS_API_KEY` | `app.py:1264`, `app.py:1303`, `app.py:2128`, `app.py:2779`, `app.py:2825`, `app.py:2826`, `app.py:2872`, `app.py:2873` | API key cuotas |
| `THESPORTSDB_API_KEY` | `app.py:1186`, `engines/sportsdb_highlights_engine.py:96` | Alias SportsDB API |
| `THESPORTSDB_KEY` | `app.py:1186`, `engines/sportsdb_highlights_engine.py:96` | SportsDB API key preferida |
| `WAREHOUSE_REFRESH_HOURS` | `engines/scheduler_engine.py:17` | Intervalo warehouse historico |
| `auto_generate_picks` | `app.py:2323` | Alias minuscula, no recomendado |
| `auto_send_telegram_picks` | `app.py:2324` | Alias minuscula, no recomendado |
| `max_auto_picks_per_day` | `app.py:2326` | Alias minuscula, no recomendado |
| `min_shark_score_for_auto_send` | `app.py:2325` | Alias minuscula, no recomendado |
| `telegram_auto_send_window_hours` | `app.py:2327` | Alias minuscula, no recomendado |

## Variables obligatorias

Obligatorias para produccion Render estable:
- `DB_PATH=/data/database.db`
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Obligatorias para datos deportivos reales:
- `THESPORTSDB_KEY` o `THESPORTSDB_API_KEY`

Obligatorias para cuotas y value/autopicks con cuota:
- `THE_ODDS_API_KEY`
- `ENABLE_ODDS_API=true`

Obligatorias para envio real Telegram:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` si no hay suscriptores Telegram vinculados en DB.

Render inyecta `PORT`; no hace falta configurarla manualmente.

## Variables opcionales

- `ADMIN_USERNAME`
- `ADMIN_NAME`
- `FLASK_DEBUG`
- `FLASK_SECRET_KEY` si no se usa `SECRET_KEY`
- `ENABLE_LIVE_API`
- `ENABLE_AUTO_SYNC`
- `AUTO_SYNC_ON_STARTUP`
- `SPORTSDB_SYNC_HOURS`
- `CREST_SYNC_HOURS`
- `ODDS_CACHE_MINUTES`
- `ODDS_REGIONS`
- `ODDS_MARKETS`
- `LIVE_CACHE_MINUTES`
- `RECOMMENDATIONS_REFRESH_MINUTES`
- `AUTO_PICKS_REFRESH_MINUTES`
- `LIVE_ALERTS_REFRESH_MINUTES`
- `WAREHOUSE_REFRESH_HOURS`
- `SCHEDULER_LOG_CLEANUP_HOURS`
- `SCHEDULER_LOG_MAX_ROWS`
- `TELEGRAM_PREPARE_HOURS`
- `POPULATION_WARMUP_HOURS`
- `POPULATION_WARMUP_LIMIT`
- `AUTO_GENERATE_PICKS`
- `AUTO_SEND_TELEGRAM_PICKS`
- `MIN_SHARK_SCORE_FOR_AUTO_SEND`
- `MAX_AUTO_PICKS_PER_DAY`
- `TELEGRAM_AUTO_SEND_WINDOW_HOURS`
- `AUTONOMOUS_CRON_TOKEN`
- `SQLITE_TIMEOUT_SECONDS`
- `SQLITE_BUSY_TIMEOUT_MS`
- `SQLITE_RETRY_ATTEMPTS`
- `SQLITE_RETRY_BASE_SLEEP`
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_ELITE`

## Variables duplicadas / aliases

- `SECRET_KEY` y `FLASK_SECRET_KEY`: usar solo `SECRET_KEY`.
- `THESPORTSDB_KEY` y `THESPORTSDB_API_KEY`: el codigo prioriza `THESPORTSDB_KEY`. Usar solo `THESPORTSDB_KEY`.
- `MIN_SHARK_SCORE_FOR_AUTO_SEND`, `AUTO_PICKS_MIN_SCORE`, `min_shark_score_for_auto_send`: usar solo `MIN_SHARK_SCORE_FOR_AUTO_SEND`.
- `MAX_AUTO_PICKS_PER_DAY` y `max_auto_picks_per_day`: usar solo `MAX_AUTO_PICKS_PER_DAY`.
- `TELEGRAM_AUTO_SEND_WINDOW_HOURS` y `telegram_auto_send_window_hours`: usar solo `TELEGRAM_AUTO_SEND_WINDOW_HOURS`.
- `AUTO_GENERATE_PICKS` y `auto_generate_picks`: usar solo `AUTO_GENERATE_PICKS`.
- `AUTO_SEND_TELEGRAM_PICKS` y `auto_send_telegram_picks`: usar solo `AUTO_SEND_TELEGRAM_PICKS`.
- `.env.example` y `env.example` son duplicados de archivo; conviene mantener uno solo.

## Variables obsoletas

Leidas por codigo, pero solo como diagnostico/legacy y no gobiernan el flujo actual principal:
- `ENABLE_TELEGRAM_AUTO`
- `TELEGRAM_AUTO_MINUTES`
- `AUTO_PICKS_MIN_SCORE` si ya usas `MIN_SHARK_SCORE_FOR_AUTO_SEND`
- `FLASK_SECRET_KEY` si ya usas `SECRET_KEY`
- `THESPORTSDB_API_KEY` si ya usas `THESPORTSDB_KEY`
- aliases en minuscula: `auto_generate_picks`, `auto_send_telegram_picks`, `min_shark_score_for_auto_send`, `max_auto_picks_per_day`, `telegram_auto_send_window_hours`

## Variables nunca utilizadas en codigo actual

Aparecen en `.env.example` / `env.example`, pero no se leen en `app.py`, `database_manager.py` ni `engines/*.py`:
- `TELEGRAM_AUTO_START_HOUR`
- `TELEGRAM_AUTO_END_HOUR`
- `OPENAI_API_KEY`
- `LIVE_CACHE_SECONDS`
- `TELEGRAM_QUEUE_ENABLED`
- `REALTIME_REFRESH_SECONDS`
- `TELEGRAM_MAX_RETRIES`
- `DISABLE_POPULATION_WARMUP`

En `render.yaml`:
- `PYTHON_VERSION` no es variable de la app, pero Render la usa para elegir runtime. No eliminar de `render.yaml` salvo que quieras dejar que Render elija version.

## Variables que puedes eliminar sin romper nada

De Render puedes eliminar con seguridad si existen:
- `TELEGRAM_AUTO_START_HOUR`
- `TELEGRAM_AUTO_END_HOUR`
- `OPENAI_API_KEY`
- `LIVE_CACHE_SECONDS`
- `TELEGRAM_QUEUE_ENABLED`
- `REALTIME_REFRESH_SECONDS`
- `TELEGRAM_MAX_RETRIES`
- `DISABLE_POPULATION_WARMUP`
- `auto_generate_picks`
- `auto_send_telegram_picks`
- `min_shark_score_for_auto_send`
- `max_auto_picks_per_day`
- `telegram_auto_send_window_hours`

Puedes eliminar tambien, si mantienes el alias recomendado:
- `FLASK_SECRET_KEY`, manteniendo `SECRET_KEY`.
- `THESPORTSDB_API_KEY`, manteniendo `THESPORTSDB_KEY`.
- `AUTO_PICKS_MIN_SCORE`, manteniendo `MIN_SHARK_SCORE_FOR_AUTO_SEND`.
- `ENABLE_TELEGRAM_AUTO` y `TELEGRAM_AUTO_MINUTES`, salvo que quieras conservarlos para diagnostico legacy.

No elimines:
- `DB_PATH`
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `THESPORTSDB_KEY` o `THESPORTSDB_API_KEY`
- `THE_ODDS_API_KEY` si quieres cuotas/autopicks con valor
- `ENABLE_ODDS_API` si quieres cuotas/autopicks con valor
- `TELEGRAM_BOT_TOKEN` si quieres Telegram real
- `TELEGRAM_CHAT_ID` si no tienes suscriptores Telegram vinculados en DB
