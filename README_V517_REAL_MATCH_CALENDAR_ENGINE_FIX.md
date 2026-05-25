# NeMeSiS SHARK PRO V517

## REAL MATCH CALENDAR ENGINE FIX

Esta build corrige el flujo de calendario real para que `match-hub`, `live`, home y perfil usen partidos persistentes en SQLite cuando existan datos legales disponibles.

### Fuentes legales preparadas

- TheSportsDB Premium mediante `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`.
- The Odds API mediante `THE_ODDS_API_KEY` y `ENABLE_ODDS_API=true`.
- Import legal CSV/JSON desde `/admin/import-center`.

### Rutas nuevas o reforzadas

- `/admin/matches-sync`
- `/api/matches/diagnostics`
- `/api/matches/sync-now`
- `/api/sportsdb/sync-matches`
- `/api/sportsdb/sync-calendar`
- `/api/odds/sync-events`
- `/api/odds/diagnostics`

### Persistencia

Mantiene `DB_PATH=/data/database.db` y añade migraciones seguras para `matches`, `live_matches` y `api_sync_logs`.

### Importante

No incluye scraping. Si las APIs no devuelven partidos, la app muestra estados premium claros y permite importar calendarios legales desde administración.
