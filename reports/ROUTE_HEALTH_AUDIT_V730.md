# Route Health Audit V730

- Versión: `V742_TOP_APP_LIVE_DETAIL_TRACK_RECORD_MATCH_INTELLIGENCE_VIDEO_HIGHLIGHTS_FINAL`
- Rutas: 230
- Templates faltantes: 0
- Resultado: OK

## Distribución por tipo
- `action`: 4
- `admin`: 51
- `admin_api`: 27
- `api`: 104
- `client`: 35
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
