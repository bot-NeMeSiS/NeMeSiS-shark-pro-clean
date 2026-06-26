# V847 API-SPORTS Runtime Admin Status QA

Endpoints añadidos:

- `/api/admin/api-sports/status`
- `/api/admin/api-sports-audit`

Vistas añadidas:

- `/admin/api-sports`
- `/admin/api-sports-audit`

Campos visibles sin secretos:

- `api_sports_configured`
- `api_football_configured`
- `provider_active`
- `fixtures_cached`
- `live_cached`
- `last_sync`
- `last_error`
- `tables_detected`
- `usage_guard`

Sin sesión admin, los endpoints JSON devuelven 403.
