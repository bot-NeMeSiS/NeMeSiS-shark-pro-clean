# Route Health Audit V730

- Versión: `V730_ARCHITECTURE_ROUTE_HEALTH_VISUAL_QA_FOUNDATION`
- Rutas: 193
- Templates faltantes: 0
- Resultado: OK

## Distribución por tipo
- `action`: 4
- `admin`: 36
- `admin_api`: 10
- `api`: 101
- `client`: 33
- `cron`: 2
- `public`: 3
- `telegram`: 4

## Templates más usados
- `password_reset_request.html`: 2
- `password_reset_form.html`: 2
- `home.html`: 1
- `global.html`: 1
- `calendar.html`: 1
- `sports_hub.html`: 1
- `live.html`: 1
- `match_hub.html`: 1
- `match_detail.html`: 1
- `team_detail.html`: 1
- `favorites.html`: 1
- `register.html`: 1

## Avisos
- `/admin-forgot-password` `admin_forgot_password_page`: admin route without visible is_admin_session check
- `/admin-reset-password/<token>` `admin_reset_password_page`: admin route without visible is_admin_session check
- `/admin-bootstrap` `admin_bootstrap_page`: admin route without visible is_admin_session check
