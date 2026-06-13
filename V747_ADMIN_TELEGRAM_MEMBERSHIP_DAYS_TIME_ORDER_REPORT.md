# V747_ADMIN_TELEGRAM_MEMBERSHIP_DAYS_TIME_ORDER_POLISH

## Base
Construido sobre el ZIP subido por el usuario: `NeMeSiS-shark-pro-clean-main(1).zip`, detectado como V745.

## Revisión del vídeo admin
Se revisó el recorrido del panel admin. Se observaron estos puntos principales:
- Navegación admin sobrecargada con demasiados accesos en la barra superior/inferior.
- Telegram tenía bot/canal configurados y cola pendiente, pero los errores eran genéricos y no explicaban si el problema era chat_id, permisos del bot, HTML, límite, etc.
- Command Center retenía envíos por ventanas/límites, pero faltaba un bloque claro de schema/memoria Telegram.
- Membresías permitían cambiar plan, pero no regalar PRO/ELITE por días.
- Horarios de cargas manuales podían desplazarse al tratar fecha+hora como UTC en vez de hora local Madrid.

## Cambios principales
### Telegram
- Nuevo envío HTTP con categorías claras de fallo: `CHAT_NOT_FOUND`, `BOT_BLOCKED`, `BOT_NOT_ADMIN_OR_MEMBER`, `HTML_PARSE_ERROR`, `MESSAGE_TOO_LONG`, `RATE_LIMITED`, `FORBIDDEN`, `BAD_REQUEST`, `NETWORK_ERROR`.
- Reintento automático en texto plano si Telegram rechaza HTML por entidades mal formadas.
- El panel muestra resultado real de la acción: procesados, enviados, fallidos, omitidos y errores accionables.
- Nuevo endpoint seguro `/api/admin/telegram/schema`.
- `telegram_delivery_memory` queda migrado para DBs antiguas sin perder historial.

### Admin ordenado
- Barra admin compactada: Control, Usuarios, Membresías, Picks, Telegram, Datos, QA, Vista cliente, Salir.
- Nuevo alias `/admin/control-center` al dashboard admin.
- Dashboard admin reorganizado por áreas y con accesos críticos: Telegram, regalar membresía, datos/horarios y QA.

### Membresías por días
- En `/admin/users` se puede asignar FREE/PRO/ELITE/ADMIN con duración: sin caducidad, 1, 3, 7, 15, 30, 60, 90, 180 o 365 días.
- Se guarda origen, nota interna, fecha de inicio, fecha de caducidad y admin que actualizó.
- Las membresías temporales caducadas bajan automáticamente a FREE al consultar usuarios/sesión.
- `/admin/memberships` muestra temporales activos, próximos a caducar y caducadas hoy.

### Horarios Madrid
- Las cargas manuales por `match_date + match_time` se tratan como hora local Madrid.
- Los ISO externos siguen pasando por el motor Madrid existente.

## Validación local
- `python -m compileall app.py engines tools` OK.
- Jinja parse de plantillas admin modificadas OK.
- `tools/check_madrid_times.py` OK.
- `tools/check_v729_security.py` OK.
- `tools/check_v733_client_success.py` OK.
- `tools/check_v735_go_live.py` OK.
- `tools/check_v739_home_data.py` OK.
- `tools/check_v742_telegram_automation.py` OK.
- `tools/check_v742_telegram_destinations.py` OK.
- `tools/check_v742_telegram_message_format.py` OK.
- `tools/check_v745_top_app_readiness.py` OK en modo static fallback por falta de Flask en sandbox.
- `tools/check_v747_admin_telegram_membership.py` OK.

## Pendiente obligatorio en Render
- Probar envío real desde `/admin/telegram` y `/admin/telegram/command-center` con `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y `AUTOMATION_SECRET` reales.
- Si el canal falla, el panel ahora debe indicar la causa accionable: chat_id incorrecto, bot sin permisos, HTML, límite, bloqueo, etc.
