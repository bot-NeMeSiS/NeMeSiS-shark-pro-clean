# V732 Production Readiness Control Center

- Versión: `V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH`
- Score: **87/100**
- Estado: **OK**
- Generado: `2026-06-12T20:22:11`

## Bloqueos
- No hay bloqueos estáticos críticos detectados.

## Avisos
- Hay basura local en raíz; el ZIP puede estar limpio, pero conviene purgar o excluir.
- Faltan variables críticas en este entorno local/sandbox; confirmar en Render antes de vender.

## Versión
- `version_txt`: `V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH`
- `app_py_version`: `V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH`
- `runtime_expected`: `V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH`
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
- Prohibidos en raíz: 1
- Directorios prohibidos: __pycache__

## Checklist Render
- `/api/runtime-version` → V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH
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
