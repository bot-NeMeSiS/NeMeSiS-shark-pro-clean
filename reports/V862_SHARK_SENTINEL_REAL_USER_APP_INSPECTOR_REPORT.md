# V862 SHARK Sentinel Real User App Inspector Report

## Qué se añadió

V862 incorpora SHARK Sentinel Bot, un inspector interno que simula perfiles de usuario y revisa rutas, pantallas, navegación, textos, estados, membresías, SHARK, Telegram, picks, live y admin.

## Componentes

- Motor: `engines/shark_sentinel_engine.py`
- Admin: `/admin/shark-sentinel`
- Alias: `/admin/app-inspector`, `/admin/qa-bot`, `/admin/bot-auditor`
- API admin summary: `/api/admin/shark-sentinel/summary`
- API admin run: `/api/admin/shark-sentinel/run`
- Cron protegido: `/api/automation/shark-sentinel/run`
- Runner local: `tools/run_shark_sentinel_static.py`

## Modos

- `MODE_STATIC_FLASK_CLIENT`: usa Flask test client y no requiere navegador.
- `MODE_BROWSER_READY`: arquitectura preparada para navegador opcional, no obligatorio.

## Límite deliberado

Sentinel no modifica código, no despliega, no toca secretos, no borra datos, no cambia pagos, no envía Telegram real y no inventa datos.
