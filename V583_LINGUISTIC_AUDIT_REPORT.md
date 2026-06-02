# V583 - Auditoría lingüística premium

## Alcance

Se revisaron las plantillas HTML de `templates/` para mejorar la experiencia visible del producto en castellano sin cambiar rutas, permisos, membresías, datos ni lógica de negocio.

## Resultado

- Textos y normalizaciones aplicadas: 1.912
- Restos de codificación corrupta en templates: 0
- Signos `?` sospechosos en textos visibles: 0
- Compilación Python de `app.py`, `engines/` y `database_manager.py`: OK

## Archivos modificados

- `templates/account_center.html`
- `templates/activity.html`
- `templates/admin_autonomous_ecosystem.html`
- `templates/admin_autonomous_picks.html`
- `templates/admin_autopilot_audit.html`
- `templates/admin_beta_center.html`
- `templates/admin_betting_center.html`
- `templates/admin_bootstrap.html`
- `templates/admin_command_center.html`
- `templates/admin_dashboard.html`
- `templates/admin_data_center.html`
- `templates/admin_data_depth.html`
- `templates/admin_intelligence_center.html`
- `templates/admin_intelligence_engine.html`
- `templates/admin_launch_center.html`
- `templates/admin_login.html`
- `templates/admin_matches_sync.html`
- `templates/admin_quality_center.html`
- `templates/admin_shark_center.html`
- `templates/admin_sportsdb_feed.html`
- `templates/admin_sportsdb_sync.html`
- `templates/admin_support_center.html`
- `templates/admin_system.html`
- `templates/admin_telegram.html`
- `templates/admin_telegram_audit.html`
- `templates/admin_user_import.html`
- `templates/admin_users.html`
- `templates/auto_picks.html`
- `templates/autonomous_ecosystem.html`
- `templates/base.html`
- `templates/betting_recommendations.html`
- `templates/calendar.html`
- `templates/client_login.html`
- `templates/client_overview.html`
- `templates/crests.html`
- `templates/daily_briefing.html`
- `templates/data_depth.html`
- `templates/discovery.html`
- `templates/ecosystem.html`
- `templates/global.html`
- `templates/home.html`
- `templates/import_center.html`
- `templates/live.html`
- `templates/match_detail.html`
- `templates/match_hub.html`
- `templates/membership.html`
- `templates/pick_tracking.html`
- `templates/picks.html`
- `templates/profile.html`
- `templates/recommendations.html`
- `templates/register.html`
- `templates/shark.html`
- `templates/shark_core.html`
- `templates/sports_intelligence.html`
- `templates/support.html`
- `templates/team_detail.html`
- `templates/telegram.html`
- `templates/unified_intelligence_hub.html`
- `V583_LINGUISTIC_AUDIT_REPORT.md`

## Correcciones realizadas

- Corrección masiva de mojibake y caracteres rotos: `Ã¡`, `Ã©`, `Ã±`, `Â·`, `â‚¬` y variantes.
- Corrección de tildes y gramática en textos visibles: `próximos`, `automático`, `membresía`, `configuración`, `sincronización`, `auditoría`, `contraseña`, `todavía`, `aquí`, `acción`, `envío`, etc.
- Sustitución de inglés innecesario en botones y títulos: `Login cliente`, `Settings`, `Dashboard`.
- Unificación de terminología de producto: cliente, panel, membresía, picks, recomendaciones, directo, Telegram, SHARK.
- Mejora de estados vacíos y avisos para que suenen más naturales y profesionales.
- Restauración de identificadores de plantilla afectados durante la normalización: `telegram_delivery`, `elite`, `crest`, `live`, `JSON`, `kickoff_time`, `stake`, `profit`.
- Corrección de dos mensajes JavaScript de seguimiento de picks que habían quedado con ternarios mal formados durante la limpieza textual.

## Pendiente de revisión manual

- Textos generados desde base de datos o introducidos por usuarios/admin no se han reescrito.
- Términos técnicos necesarios en admin se mantienen: API, JSON, SQLite, Render, TheSportsDB, Telegram, SHARK, FREE, PRO, ELITE.
- No se revisó copy dinámico construido en Python fuera de templates salvo compilación general.

## Verificación

- `app.py` compila.
- `engines/` compila.
- `database_manager.py` compila.
- Búsqueda de caracteres corruptos en templates: limpia.
- Búsqueda de signos `?` sospechosos en templates: limpia.
- No se modificó la lógica funcional de rutas, membresías, login, SHARK, Telegram ni SQLite.
