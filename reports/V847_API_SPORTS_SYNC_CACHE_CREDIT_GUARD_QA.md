# V847 API-SPORTS Sync Cache Credit Guard QA

El guard anti-gasto se implementa en `engines/api_sports_provider_engine.py`.

Controles:

- Cache primero.
- TTL por defecto configurable con `API_SPORTS_CACHE_TTL_SECONDS`.
- Timeout configurable con `API_SPORTS_TIMEOUT_SECONDS`.
- Presupuesto diario documentado con `API_FOOTBALL_DAILY_CALL_BUDGET` o `API_SPORTS_DAILY_CALL_BUDGET`.
- `dry_run=True` para auditoría sin gasto.
- Sin llamadas API desde render de pantallas cliente.
- Sin mostrar claves en JSON, logs o templates.

Resultado: calendario/live/match detail pueden seguir usando cache y sync existente, pero admin/runtime ya explican si falta proveedor o cache.
