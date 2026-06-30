# V863 Admin Routes Real QA

## Render real sin sesión admin

| Ruta | Resultado real |
|---|---|
| `/admin-login` | 200 |
| `/admin/dashboard` | 302 a `/admin-login?next=/admin/control-center` |
| `/admin/company-os` | 302 a `/admin-login?next=/admin/company-os` |
| `/admin/company-audit` | 302 a `/admin-login?next=/admin/company-audit` |
| `/admin/continuous-sentinel` | 302 a `/admin-login?next=/admin/continuous-sentinel` |
| `/admin/shark-sentinel` | 302 a `/admin-login?next=/admin/continuous-sentinel` |
| `/admin/app-inspector` | 302 a `/admin-login?next=/admin/continuous-sentinel` |
| `/admin/qa-bot` | 302 a `/admin-login?next=/admin/continuous-sentinel` |
| `/admin/bot-auditor` | 302 a `/admin-login?next=/admin/continuous-sentinel` |
| `/admin/mejora-continua` | 302 a `/admin-login?next=/admin/continuous-sentinel` |
| `/admin/data-center` | 302 a `/admin-login?next=/admin/data-center` |
| `/admin/api-sports` | 302 a `/admin-login?next=/admin/api-sports` |
| `/admin/api-sports-audit` | 302 a `/admin-login?next=/admin/api-sports` |
| `/admin/telegram/command-center` | 302 a `/admin-login?next=/admin/telegram/command-center` |
| `/admin/shark-ai` | 302 a `/admin-login?next=/admin/shark-ai` |
| `/admin/daily-automation` | 302 a `/admin-login?next=/admin/daily-automation` |
| `/admin/users` | 302 a `/admin-login?next=/admin/users` |
| `/admin/memberships` | 302 a `/admin-login?next=/admin/memberships` |
| `/admin/payments` | 302 a `/admin-login?next=/admin/payments` |

## APIs admin sin sesión

- `/api/admin/continuous-sentinel/summary`: 403
- `/api/admin/continuous-sentinel/run`: 403
- `/api/admin/continuous-sentinel/issues`: 403
- `/api/admin/company-os/summary`: 403
- `/api/admin/company-audit/summary`: 403

## Bloqueo

Credenciales admin reales no disponibles para prueba autenticada.
