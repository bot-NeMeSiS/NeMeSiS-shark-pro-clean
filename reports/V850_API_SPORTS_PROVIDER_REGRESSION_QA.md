# V850 API-SPORTS Provider Regression QA

V847 queda preservado.

Validado:

- `engines/api_sports_provider_engine.py` existe.
- `/admin/api-sports` y `/admin/api-sports-audit` se mantienen.
- `/api/admin/api-sports/status` se mantiene.
- Runtime conserva flags de API-SPORTS/API-Football/The Odds.
- Cache-first, TTL, dry-run y guard anti-gasto siguen activos.
- No hay llamadas por render.
- No se muestran secretos.
