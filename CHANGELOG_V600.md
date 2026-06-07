# CHANGELOG V600

## V600 Clean Core

- Movidos README históricos `README_V5XX*` a `docs/`.
- Creado `README_MASTER.md` como documentación principal.
- Creado `V600_AUDIT_REPORT.md`.
- Actualizado `VERSION.txt` a `V600 CLEAN CORE + V601 LIVE INTELLIGENCE`.
- Añadidas migraciones seguras para warehouse histórico.

## V601 Live Intelligence

- `engines/live_engine.py` ahora calcula:
  - `momentum_local`
  - `momentum_visitante`
  - `presion`
  - `dominancia`
  - `riesgo`
- Timeline normalizado con soporte para:
  - `goal`
  - `yellow`
  - `red`
  - `substitution`
  - `penalty`
  - `var`
- Alertas SHARK preparadas para Telegram:
  - momentum alto
  - presión extrema
  - posible gol
- `build_live_flow` agrega alertas live disponibles.

## Historical Data Warehouse

- Nuevas tablas:
  - `historical_matches`
  - `historical_picks`
  - `historical_recommendations`
- Nuevo snapshot interno `historical_snapshot()`.
- Mantiene `user_activity` existente.

## Autonomous Operations

- Scheduler ampliado con tareas:
  - `recommendations`
  - `auto_picks`
  - `live_alerts`
  - `warehouse`
- Las tareas son compatibles y conservadoras: no publican picks reales sin aprobación.

## Compatibilidad

- Render sin cambios.
- `DB_PATH=/data/database.db` intacto.
- Login, sesiones, admin, favoritos, Telegram, SHARK y membresías se mantienen.
