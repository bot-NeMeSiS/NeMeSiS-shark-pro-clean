# V904 Admin Command Center Rebuild QA

Pantallas revisadas:
- `/admin/dashboard`
- `/admin/autonomous-company-sentinel`
- `/admin/sentinel-issues`
- `/admin/sentinel-codex-outbox`

Correcciones aplicadas:
- Dashboard admin marcado como V904 y reforzado con franja de estado workforce.
- Sentinel Empresa corregido para no abrir APIs como páginas.
- Sentinel Issues y Codex Outbox usan botones seguros `data-v904-fetch`.
- Se añadió salida visible de dry-run seguro sin exponer secretos.
- Se corrigieron textos con mojibake en Sentinel Empresa.

Garantías:
- No hay navegación cliente dentro de estas plantillas V904.
- No se ejecuta deploy, push, Telegram real ni pagos.
- Las acciones admin siguen dependiendo de sesión y deben devolver 403 sin acceso.
