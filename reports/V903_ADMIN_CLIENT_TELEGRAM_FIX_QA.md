# V903 Admin Client Telegram Fix QA

## Admin
- `/admin-login`: debe cargar `200`.
- Rutas admin sin sesion deben protegerse con redirect/403, no 500.
- APIs admin sin sesion deben devolver JSON `403`.
- Admin no debe renderizar bottom nav cliente ni SHARK flotante cliente.

## Cliente
- `/`, `/cliente-login`, `/registro`, `/calendar`, `/live`, `/picks`, `/support`, `/track-record` se mantienen como pantallas seguras.
- `/app`, `/profile`, `/telegram` pueden redirigir si requieren sesion.
- 404 HTML debe ser premium.
- 404 API debe ser JSON seguro.

## Telegram
- `/api/automation/telegram/tick` sin secret: `403`.
- Con secret local falso y `dry_run`: esperado `200` local cuando se configure en entorno de prueba.
- No se envia Telegram real.
- `QUEUE_SKIPPED`, dedupe y no filler se preservan.

## Resultado
Sin errores funcionales activos reproducidos. Las acciones peligrosas quedan fuera de auto-fix.
