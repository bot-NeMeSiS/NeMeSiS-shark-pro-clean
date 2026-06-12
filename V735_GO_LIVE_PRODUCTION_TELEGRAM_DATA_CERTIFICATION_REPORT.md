# V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION

## Resumen

V735 convierte el roadmap de público grande en un panel operativo de certificación. El objetivo es saber, desde admin, si la app está lista para beta pública controlada sin tocar a ciegas producción, Telegram, pagos ni membresías.

## Añadido

- Nuevo motor: `engines/go_live_engine.py`.
- Nuevo panel admin: `/admin/go-live`.
- Alias admin: `/admin/public-beta` y `/admin/launch-certification`.
- Nueva API admin segura: `/api/admin/go-live`.
- Nueva API de plan: `/api/admin/go-live/validation-plan`.
- Nueva plantilla: `templates/admin_go_live.html`.
- Nuevo check: `tools/check_v735_go_live.py`.
- Nuevo checklist: `V735_GO_LIVE_CHECKLIST.md`.
- Capa visual V735 en `static/app.css`.
- Acceso rápido admin a Go Live.

## Qué comprueba

1. Producción Render y versión.
2. Telegram automático estable.
3. Persistencia y Data Memory.
4. Track Record, grading y ROI real.
5. Pagos PRO/ELITE en modo seguro.
6. Cliente, móvil y soporte.
7. Seguridad, tests y arquitectura.

## Seguridad

V735 es read-only: no envía Telegram, no cobra, no cambia membresías y no expone secrets. Solo muestra presencia segura de variables y contadores de tablas.

## Validación sandbox

Pendiente de ejecutar al final del empaquetado:

- `python -m py_compile app.py`
- `python -m compileall -q .`
- checks V728-V735
- build clean release
- audit release zip

## Limitación

La prueba real de Render, Telegram y Stripe solo puede cerrarse en producción con las variables reales. Esta versión deja la herramienta para hacerlo sin improvisar.
