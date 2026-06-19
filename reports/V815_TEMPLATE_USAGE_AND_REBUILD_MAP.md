# V815 Template Usage and Rebuild Map

## Cliente

| Ruta | Funcion Flask | Template real | Cambio V815 |
| --- | --- | --- | --- |
| `/` | `home` | `home.html` | Marcador `data-v815-template`, shell visible desde `base.html`, CSS V815 |
| `/app` | `v757_client_app_center_page` | `client_app_center.html` | Marcador `data-v815-template`, portada cliente premium |
| `/calendar` | `calendar_page` | `calendar.html` | Marcador `data-v815-template`, calendario central |
| `/partidos` | `calendar_page` | `calendar.html` | Mismo template real que calendario |
| `/live` | `live_page` | `live.html` | Marcador `data-v815-template`, live profesional |
| `/directo` | `live_page` | `live.html` | Alias real de live |
| `/picks` | `picks_page` | `picks.html` | Marcador `data-v815-template`, cards premium |
| `/match/<id>` | `match_detail_page` | `match_detail.html` | Marcador `data-v815-template`, detalle premium |
| `/shark` | `shark_page` | `shark.html` | Marcador `data-v815-template`, sin flotante duplicado por CSS |
| `/shark-core` | `v570_shark_core_page` | `shark_core.html` | Ruta validada, no reestructurada para evitar riesgo |
| `/telegram` | `telegram_page` | `telegram.html` | Marcador `data-v815-template`, estado claro |
| `/profile` / `/perfil` | `profile_page` | `profile.html` | Marcador `data-v815-template`, cuenta premium |
| `/favorites` | `favorites_page` | `favorites.html` | Ruta validada |
| `/track-record` | `public_track_record_page` | `track_record.html` | Ruta validada |
| `/support` | `v724_contact_alias_page` | `support.html` | Ruta validada |

## Admin

| Ruta | Template / destino | Estado |
| --- | --- | --- |
| `/admin/dashboard` | Admin dashboard/control center | Validada |
| `/admin/map` | `admin_navigation_map.html` | Validada |
| `/admin/control-center` | Admin dashboard/control center | Validada |
| `/admin/telegram/command-center` | `admin_telegram_command_center.html` | Validada |
| `/admin/telegram/pro-preview` | `admin_telegram_pro_preview.html` | Validada |
| `/admin/users` | `admin_users.html` | Validada |
| `/admin/memberships` | `admin_memberships.html` | Validada |
| `/admin/matches-sync` | `admin_matches_sync.html` | Validada |
| `/admin/data-center` | `admin_data_center.html` | Validada |
| `/admin/automation-center` | `admin_automation_center.html` | Validada |

## Enlaces principales

Cliente mantiene enlaces a `/app`, `/calendar`, `/live`, `/picks`, `/shark`, `/profile`, `/telegram`, `/support` y `/logout`.

Admin mantiene enlaces a `/admin/control-center`, `/admin/users`, `/admin/data-center`, `/admin/telegram/command-center`, `/admin/automation-center` y vista cliente.
