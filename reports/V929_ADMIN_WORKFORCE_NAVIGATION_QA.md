# V929 Admin Workforce Navigation QA

- Worker dry-run: `automation_workforce/navigation_integrity_worker.py --dry-run`.
- Panel: `/admin/navigation-integrity`, aliases `/admin/routes` y `/admin/route-health`.
- APIs admin: summary, run e issues; todas 403 sin sesion.
- Sentinel y Outbox reciben solo incidencias activas deduplicadas.
