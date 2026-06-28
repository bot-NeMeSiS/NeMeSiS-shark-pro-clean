# V857 Routes & Buttons Workers QA

## Nuevas rutas
- `/admin/company-os`
- `/admin/empresa`
- `/admin/operating-system`
- `/api/admin/company-os/summary`

## Accesos añadidos
- Navegación admin superior: `Empresa OS`.
- Rail admin: `Workers / Empresa OS`.
- Dock admin: `Empresa OS`.
- Command strip admin: `Empresa OS`.

## Protección
- El panel redirige a `/admin-login?next=/admin/company-os` si no hay sesión admin.
- La API devuelve `403` mediante `admin_json_forbidden()` si no hay sesión admin.

## Rutas críticas preservadas
- Cliente principal.
- Admin dashboard/control center.
- API-SPORTS.
- Telegram command center.
- SHARK AI.
- Daily automation.
- Users/memberships/payments.
- Runtime/master tick/health-check.
