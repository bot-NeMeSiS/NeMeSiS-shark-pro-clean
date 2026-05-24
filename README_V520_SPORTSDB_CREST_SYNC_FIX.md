# V520 — SportsDB Crest Sync Fix

Corrige el problema de que solo apareciera el escudo del Arsenal.

Incluye:
- Seed ampliado de equipos reales con IDs TheSportsDB.
- Partidos semilla con equipos reales, sin nombres falsos tipo Premier Home.
- Resolución por lookupteam.php cuando existe external_id.
- Resolución por searchteams.php con aliases y normalización.
- Sincronización admin en /admin/sportsdb-sync.
- API protegida /api/sportsdb/sync-crests.
- Diagnósticos mejorados /api/thesportsdb/diagnostics y /api/crest-diagnostics.
- Cache SQLite: no llama a TheSportsDB en cada carga.
- Fallback SVG premium si no hay logo.

Variables Render:
- THESPORTSDB_API_KEY
- THESPORTSDB_KEY
- ENABLE_LIVE_API=true
