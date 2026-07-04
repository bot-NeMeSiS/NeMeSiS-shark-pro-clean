# QA Admin Telegram Command Center V889

Nuevas APIs admin:
- `GET /api/admin/telegram/pick-candidates`
- `GET /api/admin/telegram/pick-preview`
- `POST /api/admin/telegram/pick-dry-run`
- `GET /api/admin/telegram/pick-quality-summary`

Sin sesion admin:
- Todas deben devolver 403.

Dry-run:
- No envia Telegram.
- No escribe cola.
- Devuelve score, motivos, dedupe key, variante por membresia y preview del mensaje.
