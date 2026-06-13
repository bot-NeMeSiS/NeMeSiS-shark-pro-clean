# V748 Admin Client Telegram Security Production Hotfix

## Estado

Versión final: `V748_ADMIN_CLIENT_TELEGRAM_SECURITY_PRODUCTION_HOTFIX`.

Esta versión consolida la base actual sin rehacer la app: arregla rutas rotas, admin, SHARK, seguridad de APIs, Telegram diagnostics, membresías temporales y release limpio Render Ready.

## Fallos reales corregidos

- `/admin/data-center` y `/admin/matches-sync` dejaban 500 por variable Jinja corrupta `matches_díagnostics`. Se normalizó a `matches_diagnostics`.
- `/partidos` estaba duplicada. Ahora queda solo en calendario/listado premium.
- `/shark-core` fallaba porque `build_daily_briefing()` no aceptaba contexto opcional. Se amplió la firma de forma compatible.
- `/inteligencia` ya carga la pantalla SHARK directamente con 200 en sesión cliente.
- Faltaba `/api/admin/control-center`. Se añadió con protección admin y resumen operativo sin secrets.
- APIs técnicas sensibles abiertas quedaron protegidas.

## Cambios admin

- Navegación ordenada en bloques: Control, Clientes, Membresías, Picks, Telegram, Datos, QA/Venta, Vista cliente y Salir.
- `/api/admin/control-center` devuelve estado de versión, DB, Data Memory, Telegram, cron, membresías temporales, rutas críticas y errores seguros.
- Aliases seguros para rutas legacy: `/admin/live-depth`, `/seguimiento`, `/soporte`, `/membresías`.

## Cambios Telegram

- `/api/telegram/auto-run` exige admin o `AUTOMATION_SECRET`.
- Cron sin secret devuelve 403.
- Cron con secret devuelve 200.
- No se envía Telegram real durante QA local.
- El schema de `telegram_delivery_memory` queda validado.

## Cambios membresías

- Reforzada migración segura para membresías temporales.
- Añadida columna `membership_admin_granted`.
- Se mantienen fecha de inicio, caducidad, nota, quién actualizó y fuente.
- La caducidad automática baja a FREE sin borrar historial y sin tocar ADMIN.

## Seguridad

Protegidas:

- `/api/diagnostics`
- `/api/cache/status`
- `/api/matches/diagnostics`
- `/api/odds/diagnostics`
- `/api/telegram/auto-run`
- `/api/profile`

## Horarios Madrid

Madrid Time sigue validado con `tools/check_madrid_times.py`.

## Validaciones

- `compileall app.py engines tools`: OK
- Jinja principal: OK
- Smoke Flask público/cliente/admin: OK
- Cron sin secret: 403
- Cron con secret: 200
- Security check: OK
- Home data check: OK
- Telegram checks V742: OK
- Data Vault: OK
- Production readiness: OK
- Top App readiness: OK
- Check V748 production hotfix: OK

## Limitaciones locales

- No se validaron secrets reales de Render.
- No se envió Telegram real.
- No se verificó canal/privado real en producción.

## Próximo paso recomendado

V749 debe ser certificación real en Render: cron real, Telegram real, DB persistente `/data/database.db`, Data Vault en `/data/backups` y revisión de errores en producción.
