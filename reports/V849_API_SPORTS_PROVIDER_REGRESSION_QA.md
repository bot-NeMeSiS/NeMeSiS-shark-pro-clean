# V849 API-SPORTS Provider Regression QA

Validado:

- `engines/api_sports_provider_engine.py` existe.
- `/admin/api-sports` y `/admin/api-sports-audit` preservados.
- `/api/admin/api-sports/status` preservado.
- Runtime mantiene flags seguros.
- Guard cache-first, TTL, dry-run y presupuesto diario preservados.
- No llamadas API por render visual.
