# V828 Routes Buttons Links Audit

## Cliente

| Ruta | Template real | Estado V828 | Botones revisados |
|---|---|---|---|
| `/` | `home.html` | Cubierta | Entrar, crear cuenta, planes, confianza |
| `/cliente-login` | `client_login.html` | Cubierta | Entrar, registro |
| `/registro` | `register.html` | Cubierta | Crear cuenta, login |
| `/app` | `client_app_center.html` | Cubierta | Partidos, Directo, Picks, SHARK, Telegram, Histórico |
| `/calendar` | `calendar.html` | Cubierta | Hoy, semana, directo, picks, detalle |
| `/partidos` | `calendar.html` o alias equivalente | Cubierta por V828 | Detalle, analizar partido, filtros |
| `/live` | `live.html` | Cubierta | Agenda, SHARK, tracker, detalle |
| `/directo` | `live.html` o alias equivalente | Cubierta por V828 | Detalle, SHARK |
| `/picks` | `picks.html` | Cubierta | Ver análisis, preguntar SHARK, combis |
| `/match/<id>` | `match_detail.html` | Cubierta | Volver, partidos, picks, SHARK |
| `/shark` | `shark.html` | Cubierta | Picks, combi, Telegram, menú |
| `/shark-ai` | ruta SHARK equivalente si existe | Cubierta por bloqueo de floating | Sin floating duplicado |
| `/shark-core` | `shark_core.html` | Cubierta | SHARK core, sin floating duplicado |
| `/profile` | `profile.html` | Cubierta | Mi cuenta, favoritos, Telegram, salir |
| `/telegram` | `telegram.html` | Cubierta | Conectar, nuevo código, mi cuenta, picks |
| `/support` | `support.html` | Cubierta | Ayuda, Telegram, cuenta |
| `/favorites` | `favorites.html` | Cubierta | Estrella/favoritos y detalle |
| `/track-record` | `track_record.html` | Cubierta | Histórico y picks |
| `/combis` | `combis.html` | Cubierta | Picks, SHARK |
| `/mercados` | `betting_markets.html` | Cubierta | Mercados y picks |
| `/highlights` | `highlights.html` | Cubierta | Detalle si existe |

## Admin

| Ruta | Template real | Estado V828 | Botones revisados |
|---|---|---|---|
| `/admin/dashboard` | `admin_dashboard.html` | Cubierta | Usuarios, datos, picks, Telegram |
| `/admin/map` | `admin_navigation_map.html` | Cubierta | Mapa completo |
| `/admin/control-center` | command center/admin dashboard | Cubierta por shell admin | Accesos principales |
| `/admin/daily-automation` | `admin_daily_automation.html` | Cubierta | Master tick, automation |
| `/admin/automation-os` | `admin_automation.html` o centro equivalente | Cubierta | Cron/automation |
| `/admin/telegram/command-center` | `admin_telegram_command_center.html` | Cubierta | Envío, diagnóstico, cola |
| `/admin/users` | `admin_users.html` | Cubierta | Usuarios y membresías |
| `/admin/memberships` | `admin_memberships.html` | Cubierta | Planes |
| `/admin/matches-sync` | `admin_matches_sync.html` | Cubierta | Sync seguro |
| `/admin/data-center` | `admin_data_center.html` | Cubierta | APIs, datos |
| `/admin/payments` | `admin_payments.html` | Cubierta | Pagos |
| `/admin/final-certification` | `admin_final_certification.html` | Cubierta | Certificación |

## Cambios aplicados

- Se añadió rail cliente desktop con enlaces reales: Dashboard, Partidos, Directo, Picks, SHARK, Histórico, Telegram, Perfil, Soporte y Salir.
- En móvil se mantiene una sola bottom nav.
- Se neutraliza floating SHARK en `/shark`, `/shark-ai` y `/shark-core`.
- El título ya no contiene el literal `{{ title or 'NeMeSiS SHARK PRO' }}`.
- No se detectaron botones V828 nuevos sin destino.

## Revisión manual pendiente

Algunas rutas antiguas siguen existiendo por compatibilidad histórica. No se eliminan en V828 para no romper enlaces externos ni automatizaciones.
