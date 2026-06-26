# V847 Data Center Provider Visibility QA

Data Center ahora incluye `api_sports_provider` dentro de `data_center_summary()`.

Impacto:

- Admin puede distinguir SportsDB, The Odds API y API-SPORTS/API-Football.
- API-SPORTS se presenta como proveedor de fixtures/live/detail, no como proveedor de cuotas.
- The Odds API se mantiene como proveedor de cuotas.
- Si Render no tiene key, el estado queda claro sin romper cliente.

Pendiente opcional: mover el panel visual dentro de `admin_data_center.html` en V848 si se quiere más integración visual. En V847 ya existe ruta dedicada.
