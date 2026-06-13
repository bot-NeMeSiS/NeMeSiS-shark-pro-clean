# V759 CLIENT ADMIN QA CHECKLIST

## Cliente

- `/`: home comercial y app unificada.
- `/app`, `/mi-app`, `/inicio`, `/panel-cliente`: centro cliente V757.
- `/picks`: picks premium con lectura SHARK.
- `/calendar`, `/calendario`, `/partidos`: calendario con filtros y hora Madrid.
- `/live`, `/directo`, `/en-directo`: directo compacto.
- `/track-record`: transparencia sin ROI inventado.
- `/experiencia`, `/modo-app`, `/adaptive`, `/adaptativo`: experiencia PC/móvil V758.
- `/telegram`: vinculación y valor por plan sin exponer secretos.

## Admin

- `/admin/dashboard`: resumen ejecutivo.
- `/admin/control-center`: panel operativo.
- `/admin/telegram/command-center`: Telegram/Cron.
- `/admin/data-center`: datos y sincronización.
- `/admin/matches-sync`: partidos.
- `/admin/client-success`: éxito cliente.
- `/admin/go-live`: salida a producción.
- `/admin/final-release`: release final.
- `/admin/sale-ready`: venta.

## APIs y Cron

- `/api/runtime-version`
- `/api/client/app-center`
- `/api/client/trust-snapshot`
- `/api/client/device-experience`
- `/api/admin/telegram/environment-audit`
- `/api/admin/telegram/auto-candidates`
- `/api/automation/telegram/tick`

## Criterios

- Sin 500 en rutas críticas.
- Cron sin secret devuelve 403.
- Cron con secret devuelve 200.
- Admin protegido sin sesión.
- ZIP final sin archivos prohibidos.
