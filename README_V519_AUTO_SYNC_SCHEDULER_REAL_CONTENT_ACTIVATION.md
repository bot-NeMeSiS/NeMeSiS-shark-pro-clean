# NeMeSiS SHARK PRO V519

## AUTO SYNC SCHEDULER + REAL CONTENT ACTIVATION

Esta build activa un scheduler interno seguro para que la app pueda poblar contenido sin depender solo de botones manuales.

### Engine nuevo

- `engines/scheduler_engine.py`

### Tareas automaticas

- Calendario SportsDB.
- Equipos y escudos.
- Cuotas Odds.
- Refresh live basico.
- Limpieza de logs.
- Preparacion Telegram futura.

### SQLite

- Nueva tabla `scheduler_locks`.
- Uso de `api_sync_logs` para trazabilidad.
- Locks por tarea, intervalos configurables y proteccion contra tareas duplicadas.

### Variables

- `ENABLE_AUTO_SYNC=true`
- `AUTO_SYNC_ON_STARTUP=true`
- `SPORTSDB_SYNC_HOURS=6`
- `CREST_SYNC_HOURS=24`
- `LIVE_CACHE_MINUTES=2`
- `ODDS_CACHE_MINUTES=20`
- `SCHEDULER_LOG_CLEANUP_HOURS=24`
- `SCHEDULER_LOG_MAX_ROWS=300`

No usa scraping. Si una API no devuelve datos o falta una key, la app no rompe y muestra estados premium claros.
