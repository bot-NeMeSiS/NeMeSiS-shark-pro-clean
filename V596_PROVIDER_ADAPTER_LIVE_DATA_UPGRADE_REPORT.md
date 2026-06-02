# V596 — Provider Adapter & Live Data Upgrade

## Objetivo
Preparar NeMeSiS SHARK PRO para integrar una fuente profesional de datos en vivo sin rehacer la aplicación.

## Añadido
- Motor `engines/data_provider_engine.py`.
- Contrato común para partidos, eventos y alineaciones.
- Preparación para TheSportsDB, API-Football, Sportmonks, Sportradar y The Odds API.
- Fallback configurable por variables de entorno.
- Tablas SQLite seguras:
  - `data_provider_runs`
  - `data_provider_cache`
  - `data_provider_mapping`
  - `provider_health_snapshots`
- Integración en Admin Data Center.
- Endpoints:
  - `/api/data-provider/summary`
  - `/api/data-provider/check`
  - `/api/v596/provider-adapter-check`

## Variables nuevas recomendadas
```env
PRIMARY_FOOTBALL_DATA_PROVIDER=thesportsdb
FOOTBALL_DATA_PROVIDER_ORDER=thesportsdb,api_football,sportmonks,sportradar
API_FOOTBALL_KEY=
SPORTMONKS_API_KEY=
SPORTRADAR_API_KEY=
ENABLE_API_FOOTBALL_PROVIDER=false
ENABLE_SPORTMONKS_PROVIDER=false
ENABLE_SPORTRADAR_PROVIDER=false
```

## Nota legal
La capa está pensada para APIs, feeds autorizados y datos con licencia clara. No usa scraping de webs oficiales ni de apps de terceros.

## QA
- `compileall app.py engines` OK.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs internos.
