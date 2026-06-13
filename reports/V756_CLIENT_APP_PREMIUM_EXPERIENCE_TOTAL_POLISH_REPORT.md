# V756 Client App Premium Experience Total Polish

## Versión
`V756_CLIENT_APP_PREMIUM_EXPERIENCE_TOTAL_POLISH`

## Objetivo
Avance grande de experiencia cliente sin tocar Telegram/Cron/DB_PATH: inicio premium, picks más comerciales, calendario guiado, detalle de partido más claro y navegación enlazada.

## Cambios principales
- Nuevo engine `engines/client_app_premium_engine.py` para construir contexto cliente defensivo.
- Home con centro cliente SHARK: KPIs, próximos focos, picks activos y accesos rápidos.
- Picks con centro de picks, filtros comerciales y resumen visual.
- Calendario con agenda inteligente, enlaces rápidos y lectura de ordenado por directo/picks/favoritos/hora Madrid.
- Detalle de partido con centro del partido y acciones rápidas.
- CSS responsive V756 para móvil/web.
- Se conserva Telegram V754, runner Cron, secrets y DB_PATH.

## No tocado
- `tools/render_cron_telegram_tick.py`.
- `/api/automation/telegram/tick`.
- `AUTOMATION_SECRET` y variables reales.
- Persistencia de usuarios/picks/Telegram.

## Validación esperada
Compilación Python, parse Jinja, smoke de rutas cliente/admin críticas y ZIP limpio.
