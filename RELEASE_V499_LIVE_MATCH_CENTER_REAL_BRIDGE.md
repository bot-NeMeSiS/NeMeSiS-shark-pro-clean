# V499 — LIVE MATCH CENTER REAL BRIDGE

Avance principal del bloque número 1: LIVE real.

## Incluye
- Nuevo `/live-match-center` premium.
- Nueva API `/api/v499/live-match-center`.
- Nuevo diagnóstico `/api/v499/live-diagnostics`.
- Conexión legal a TheSportsDB para live cuando esté disponible.
- Caché persistente SQLite `live_match_cache_v499`.
- Fallback interno desde picks/partidos guardados.
- Clasificación automática: en vivo, programados y finalizados.
- Preparado para eventos/timeline/estadísticas live sin scraping ilegal.

## Legalidad
No se hace scraping. Solo API legal/configurada, caché propia y datos persistidos propios.

## Variables recomendadas
ENABLE_LIVE_API=true
THESPORTSDB_KEY=123
THESPORTSDB_API_KEY=123
LIVE_CACHE_MINUTES=2

## Rutas nuevas
/live-match-center
/live-match-center-v499
/api/v499/live-match-center
/api/v499/live-diagnostics
/v499-health
