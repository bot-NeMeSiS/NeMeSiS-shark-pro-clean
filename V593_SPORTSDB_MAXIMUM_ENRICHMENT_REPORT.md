# V593 — TheSportsDB Maximum Enrichment

## Objetivo
Aprovechar al máximo TheSportsDB como fuente legal/autorizada para enriquecer NeMeSiS SHARK PRO con más contexto deportivo sin scraping.

## Añadido
- Nuevo motor `engines/sportsdb_enrichment_engine.py`.
- Caché SQLite propia para datos enriquecidos de TheSportsDB.
- Perfiles de ligas, equipos y eventos.
- Datos de estadios, países, temporadas, escudos, logos, descripciones y eventos pasados/futuros cuando la API los ofrece.
- Enlace de eventos TheSportsDB con partidos internos cuando hay coincidencia por ID o equipos/fecha.
- Bloque V593 en la ficha de partido con contexto oficial TheSportsDB.
- Bloque V593 en Admin Data Center para sincronizar y auditar el enriquecimiento.
- Endpoints:
  - `/api/sportsdb-enrichment/summary`
  - `/api/sportsdb-enrichment/sync`
  - `/api/v593/sportsdb-enrichment-check`

## Tablas nuevas
- `sportsdb_data_sources`
- `sportsdb_league_profiles`
- `sportsdb_team_profiles`
- `sportsdb_event_profiles`
- `sportsdb_enrichment_runs`

## Legalidad y seguridad
- No se ha implementado scraping.
- El sistema usa TheSportsDB API con `THESPORTSDB_KEY` o `THESPORTSDB_API_KEY`.
- Los datos se guardan en SQLite como caché propia para reducir llamadas y mejorar rendimiento.
- Se añade nota legal/atribución de fuente en resumen y ficha.

## QA
- `compileall app.py engines` OK.
- Prueba SQLite temporal del esquema y resumen OK.
- ZIP limpio sin `.git`, `__pycache__`, bases de datos locales, logs ni ZIPs internos.

## Archivos modificados
- `app.py`
- `engines/sportsdb_enrichment_engine.py`
- `templates/admin_data_center.html`
- `templates/match_detail.html`
- `VERSION.txt`
