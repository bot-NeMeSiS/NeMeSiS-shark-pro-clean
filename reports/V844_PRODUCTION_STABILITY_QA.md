@"
# V844 Production Stability QA

## Preservado
- V818 master tick.
- V843 comercial review.
- Render Cron.
- Telegram automático.
- DB_PATH.
- Madrid Time.
- Usuarios, sesiones, membresías y pagos.
- API-Football y The Odds API.
- Sistema ligero de escudos.

## Validación pendiente en este informe
Los resultados finales se añaden tras ejecutar compileall, smoke Flask, checks V843/V844 y auditoría del ZIP.

## Validación ejecutada
- py_compile app.py: OK.
- compileall app.py engines tools: OK.
- Parse Jinja: 151 templates, 0 errores.
- check_madrid_times.py: OK.
- check_v843_routes_actions.py: OK.
- check_v843_real_data_commercial_states.py: OK.
- check_v844_runtime_visibility.py: OK.
- check_v844_telegram_quality_filter.py: OK.
- check_v844_telegram_no_filler.py: OK.
- check_v844_telegram_message_cards.py: OK.
- check_v844_picks_app_telegram_consistency.py: OK.
- check_v844_admin_telegram_quality_center.py: OK.
- check_v844_app_match_quality_hierarchy.py: OK.
- check_v844_v818_to_v843_compatibility.py: OK.
- Smoke Flask V844: OK.
- Master tick sin secret: 403 OK.
- Master tick con secret dry_run=1: 200 OK.
- Health-check con secret: 200 OK.

## Nota local
No se enviaron mensajes reales de Telegram en local.
