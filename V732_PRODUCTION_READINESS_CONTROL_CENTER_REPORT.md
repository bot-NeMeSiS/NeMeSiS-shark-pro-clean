# V732 Production Readiness Control Center

- Versión: `V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH`
- Score: **71/100**
- Estado: **REVISAR**
- Generado: `2026-06-13T00:56:52`

## Bloqueos
- No hay bloqueos estáticos críticos detectados.

## Avisos
- Hay basura local en raíz; el ZIP puede estar limpio, pero conviene purgar o excluir.
- Faltan variables críticas en este entorno local/sandbox; confirmar en Render antes de vender.

## Versión
- `version_txt`: `V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH`
- `app_py_version`: `V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH`
- `runtime_expected`: `V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH`
- `match`: `True`
- `has_recent_stack`: `False`

## Variables seguras
- SECRET_KEY estable: pendiente · severidad WARN
- Secret Cron: pendiente · severidad WARN
- Ruta DB: pendiente · severidad WARN esperado `/data/database.db`
- Bot token Telegram: pendiente · severidad INFO
- Chat/canal Telegram: pendiente · severidad INFO
- URL pública: pendiente · severidad INFO
- The Odds API: pendiente · severidad INFO

## Centros admin
- Telegram Command Center: ruta OK · template OK
- Salud de rutas: ruta OK · template OK
- Experiencia cliente: ruta OK · template OK
- Diagnóstico hora Madrid: ruta OK · template OK
- Memoria SHARK: ruta OK · template OK

## Limpieza
- Prohibidos en raíz: 5
- Directorios prohibidos: .git, .pytest_cache, .venv, __pycache__, v636work

## Checklist Render
- `/api/runtime-version` → V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH
- `/api/health` → 200 / OK si existe
- `/api/automation/telegram/tick` → 403
- `/api/automation/telegram/tick?secret=***` → 200
- `/api/automation/daily/run` → 403
- `/api/automation/daily/run?secret=***` → 200

## Próximos pasos
- Subir ZIP limpio a Render y confirmar /api/runtime-version.
- Confirmar DB_PATH=/data/database.db y disco persistente en Render.
- Probar Cron Telegram/Daily 403 sin secret y 200 con secret sin compartir secrets.
- Entrar en /admin/telegram/command-center para ver causa real si Telegram no envía.
- Revisar /admin/client-experience y /admin/route-health tras cada release.
- Grabar QA móvil real de Home, Calendar, Live, Picks, Combis, SHARK, Telegram y Match Detail.
