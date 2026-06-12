# V579 — SportsDB Highlights & Past Match Intelligence

Avance enfocado en aprovechar TheSportsDB Premium para partidos pasados y resúmenes.

## Añadido

- Motor `engines/sportsdb_highlights_engine.py`.
- Tablas SQLite para highlights, enriquecimiento por partido y runs.
- Sincronización por fecha usando `eventshighlights.php`.
- Enlace inteligente con partidos guardados por `external_id` o por fecha/equipos.
- Ficha de partido con bloque “Resumen del partido”.
- Data Center con panel de SportsDB Highlights.
- APIs:
  - `/api/sportsdb-highlights/summary`
  - `/api/sportsdb-highlights/sync`
  - `/api/sportsdb-highlights/rebuild`
  - `/api/system/v579-check`

## Render

Configurar una de estas variables:

- `THESPORTSDB_API_KEY`
- `THESPORTSDB_KEY`

Opcional:

- `SPORTSDB_LIVE_ENABLED=1`

## Nota

TheSportsDB ofrece highlights de YouTube asociados a eventos. Pueden no existir para todos los partidos o estar geobloqueados según YouTube/fuente externa.
