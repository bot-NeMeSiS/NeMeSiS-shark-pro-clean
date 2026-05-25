# NeMeSiS SHARK PRO V518

## MASSIVE FOOTBALL DATA POPULATION ENGINE

Esta build añade una capa de poblacion masiva legal para que la app deje de depender de pantallas vacias.

### Incluye

- Engine `engines/football_population_engine.py`.
- Data Center admin en `/admin/data-center`.
- Sincronizacion de competiciones, equipos, escudos, calendario, resultados y cuotas.
- Tabla `odds_snapshots`.
- Indices SQLite para calendario, equipos, competiciones y logs.
- Warmup seguro con intervalo configurable y sin bloquear Flask.

### Fuentes permitidas

- TheSportsDB Premium.
- The Odds API.
- Import legal CSV/JSON desde `/admin/import-center`.
- Seeds estructurales de competiciones y equipos reales, nunca partidos falsos como reales.

### Variables utiles

- `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`
- `ENABLE_LIVE_API=true`
- `THE_ODDS_API_KEY`
- `ENABLE_ODDS_API=true`
- `ODDS_CACHE_MINUTES`
- `ODDS_REGIONS`
- `ODDS_MARKETS`
- `POPULATION_WARMUP_HOURS`
- `POPULATION_WARMUP_LIMIT`
- `DISABLE_POPULATION_WARMUP=true` si se quiere desactivar el warmup automatico.
