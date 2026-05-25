# NeMeSiS SHARK PRO — V519 AUTO SYNC SCHEDULER REAL CONTENT ACTIVATION

Build limpia normalizada para Render/GitHub.

Incluye:
- V518 Massive Football Data Population Engine
- V519 Auto Sync Scheduler Engine
- Data Center admin
- Scheduler locks persistentes
- Warmup seguro
- Sync calendario/equipos/escudos/cuotas/live
- Estados premium sin datos falsos
- SQLite WAL/timeout/migraciones seguras

Variables recomendadas:
```env
DB_PATH=/data/database.db
SECRET_KEY=...
THESPORTSDB_API_KEY=...
THESPORTSDB_KEY=...
ENABLE_LIVE_API=true
THE_ODDS_API_KEY=...
ENABLE_ODDS_API=true
ENABLE_AUTO_SYNC=true
AUTO_SYNC_ON_STARTUP=true
SPORTSDB_SYNC_HOURS=6
CREST_SYNC_HOURS=24
LIVE_CACHE_MINUTES=2
ODDS_CACHE_MINUTES=20
ODDS_REGIONS=eu
ODDS_MARKETS=h2h,totals
```

Rutas clave:
- /admin/data-center
- /api/scheduler/status
- /api/scheduler/run-now
- /api/matches/diagnostics
- /match-hub
- /live
- /api/health
