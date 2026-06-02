# V572 — Historical Data Warehouse

Avance centrado en datos, no en pantallas nuevas.

## Objetivo
Convertir la base SQLite persistente en una capa historica preparada para SHARK, automatizacion y futuro Machine Learning.

## Incluye
- Nuevo engine `engines/historical_warehouse_engine.py`.
- Tablas warehouse seguras:
  - `warehouse_match_facts`
  - `warehouse_odds_facts`
  - `warehouse_pick_facts`
  - `warehouse_user_facts`
  - `warehouse_daily_metrics`
  - `warehouse_sync_runs`
- Snapshot historico manual desde Admin Data Center.
- Snapshot historico automatico desde scheduler task `warehouse`.
- Nuevas APIs admin:
  - `/api/warehouse/summary`
  - `/api/warehouse/snapshot`
- Admin Data Center enriquecido con metricas warehouse.

## Filosofia
El admin supervisa. SHARK piensa. El ecosistema guarda datos y aprende.

## Seguridad
- No borra datos existentes.
- Usa `INSERT OR REPLACE` / `INSERT OR IGNORE`.
- Compatible con `/data/database.db` en Render.
- Mantiene cache, usuarios, picks, cuotas y partidos existentes.
