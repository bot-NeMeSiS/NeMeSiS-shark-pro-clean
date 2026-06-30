# V863 Real World Certification Matrix

| Área | Estado | Evidencia | Bloqueo / siguiente acción |
|---|---|---|---|
| Render deploy | partially_certified | Producción responde V862 HTTP 200 | Deploy V863 pendiente |
| Runtime | partially_certified | `/api/runtime-version` devuelve V862 y flags críticos | Revalidar tras deploy V863 |
| Header sanitization | certified_local | Check V863 local añadido | Confirmar en Render tras deploy |
| Public routes | certified | Rutas públicas reales 200/302 esperado | Visual browser pendiente |
| Client auth | partially_certified | Privadas redirigen a login | Login real sin credenciales |
| Admin auth | certified | Admin redirige/403 sin sesión | Prueba autenticada pendiente |
| Company OS | partially_certified | Ruta protegida 302 | Acceso admin pendiente |
| Company Audit | partially_certified | Ruta/API protegida | Acceso admin pendiente |
| Continuous Sentinel | partially_certified | APIs admin 403, cron 403 sin secret, runner local | Secret real no disponible |
| Master tick | partially_certified | 403 sin secret | Dry-run con secret pendiente |
| Health-check | partially_certified | 403 sin secret | Prueba con secret pendiente |
| API-SPORTS | partially_certified | Runtime: configurado, guard activo, last_sync conocido | No se gastó llamada nueva |
| The Odds API | partially_certified | Runtime: configurado | No se gastó llamada nueva |
| Telegram | partially_certified | Runtime: configurado | No se envió test real |
| Payments | blocked | Motor/rutas presentes | Stripe test keys no disponibles |
| SHARK IA | certified_local | Checks heredados V845/V862 | OpenAI no configurado en runtime |
| PC visual | not_available | No browser real | Ejecutar Playwright |
| Mobile visual | not_available | No browser real | Ejecutar Playwright |
| Security | certified | 403/302 y no secretos visibles | Auditoría autenticada pendiente |
| Release ZIP | pending | Se genera al final de V863 | Auditar `forbidden_count=0` |

## Nota local DB_PATH

El primer smoke local heredó `DB_PATH=/data/database.db`, ruta no escribible en Windows, y produjo 500 locales. No se cambió `DB_PATH` del producto. El smoke se repitió con una base temporal de QA y todas las rutas críticas quedaron sin 500.
