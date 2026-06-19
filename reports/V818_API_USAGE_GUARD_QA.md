# V818 API Usage Guard QA

`engines/api_usage_guard_engine.py` registra estimaciones por proveedor y fecha Madrid.

Variables soportadas:

- `API_FOOTBALL_DAILY_CALL_BUDGET`
- `ODDS_API_DAILY_CALL_BUDGET`
- `ENABLE_AUTO_FIXTURE_SYNC`
- `ENABLE_AUTO_RESULTS_SYNC`
- `ENABLE_AUTO_LIVE_SYNC`
- `ENABLE_AUTO_ODDS_SYNC`

Politica:

- Cache primero.
- Ligas top primero.
- No consultar ligas raras para Telegram.
- Saltar jobs si el presupuesto estimado queda agotado.
- Fallback a DB/cache si una API falla.
