# V891 Telegram Premium Admin Endpoint Compatibility

Version: `V891_TELEGRAM_PREMIUM_ADMIN_ENDPOINT_COMPATIBILITY_FINAL`.

Objetivo: cerrar los nombres de endpoints recomendados en el brief V889 sin duplicar logica ni enviar Telegram real.

Endpoints nuevos/alias protegidos:
- `/api/admin/telegram/pick-quality`
- `/api/admin/telegram/premium-preview`
- `/api/admin/telegram/dry-run-premium-picks`
- `/api/admin/telegram/blocked-picks`
- `/api/admin/telegram/quality-status`

Todos reutilizan la inteligencia V889:
- motor de calidad;
- preview por membresia;
- bloqueo por falta de cuota/seleccion/partido real;
- no filler;
- dedupe;
- `QUEUE_SKIPPED`.

Sin sesion admin deben responder 403.
Dry-run premium no envia Telegram real y no escribe cola.
