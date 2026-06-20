# V841 Telegram Cron Admin Final QA

- Master tick: se conserva.
- Health-check: se conserva.
- Telegram automático: no se modifica.
- Admin Telegram: mantiene separación visual admin/cliente.
- `/api/automation/master-tick?dry_run=1` sin secret: 403.
- `/api/automation/master-tick?secret=...&dry_run=1`: 200.
- `/api/automation/health-check?secret=...`: 200.
- `/admin/telegram/command-center`: 302 sin sesión, sin error 500.
