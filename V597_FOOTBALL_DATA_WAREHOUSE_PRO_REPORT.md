# V597 — Football Data Warehouse Pro

## Objetivo

Convertir NeMeSiS SHARK PRO en un ecosistema que guarda memoria deportiva desde hoy y para siempre: partidos, eventos, equipos, cuotas y señales SHARK. Esta capa no revende datos crudos de terceros; conserva snapshots internos para operar la app, mejorar SHARK, calcular métricas propias y crear activos derivados de NeMeSiS.

## Añadido

- Nuevo motor `engines/football_data_warehouse_engine.py`.
- Tablas SQLite seguras:
  - `football_dw_sync_runs`
  - `football_matches_history`
  - `football_match_events_history`
  - `football_lineups_history`
  - `football_standings_history`
  - `football_team_snapshots`
  - `football_odds_history`
  - `football_shark_signals_history`
  - `football_derived_assets`
- Snapshots desde tablas internas actuales:
  - `matches`
  - `live_event_history`
  - `match_timeline`
  - `teams`
  - `odds_snapshots`
  - `picks`
- Pull opcional desde API-Football si existe `API_FOOTBALL_KEY`.
- Enriquecimiento automático dentro de la tarea scheduler `warehouse`.
- Panel nuevo en Admin Data Center.
- Endpoints:
  - `/api/football-warehouse/summary`
  - `/api/football-warehouse/sync`
  - `/api/v597/football-warehouse-check`

## Variables recomendadas Render

```env
API_FOOTBALL_KEY=tu_clave_pro
ENABLE_API_FOOTBALL_PROVIDER=true
ENABLE_FOOTBALL_WAREHOUSE_API_PULL=true
FOOTBALL_WAREHOUSE_DAYS_BACK=3
FOOTBALL_WAREHOUSE_DAYS_AHEAD=7
WAREHOUSE_REFRESH_HOURS=12
```

## Legalidad y uso correcto

El warehouse está preparado para uso interno: SHARK, picks, ratings, value, ROI, learning y métricas propias. No se debe redistribuir ni revender el feed crudo de terceros sin licencia específica del proveedor.

## QA

- `compileall app.py engines database_manager.py` OK.
- Prueba SQLite temporal del motor V597 OK.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs internos.
