# TELEGRAM RELIABILITY REPORT

Fecha Madrid: 2026-07-30
Modo: read-only + pruebas locales sin secretos
Produccion modificada: false
Telegram enviado: false
Mensajes enviados: 0
Cron ejecutado: false
Secretos expuestos: 0

## Decision

TELEGRAM RELIABILITY: BLOCKED

Hay senales positivas de configuracion y tick reciente, pero la certificacion real controlada no puede cerrarse sin acceso a token/admin/Render. No se envia el mensaje autorizado porque no se cumplen las precondiciones de seguridad.

## Evidencia de fiabilidad

| Area | Estado | Evidencia | Riesgo restante |
|---|---|---|---|
| Scheduler | PARTIAL | `scheduler_enabled=true`, `daily_automation_enabled=true` | Sin logs Render. |
| Cron Telegram | PARTIAL | `v937_cron_telegram_status=RECENT`, ultimo tick 07:40:04 Madrid | No se conoce resultado interno del tick. |
| Cron Sports compartido | PARTIAL | `v937_sports_cron_status=PARTIAL`, evidencia operacional reciente | Gate 2 sigue bloqueado por Cron/Master Tick. |
| Proteccion de acciones | PASS | Rutas admin/dry-run/status devuelven 403 sin sesion | No certifica contenido interno. |
| No spam | PASS | Limites horario, diario, quiet hours y max queue per tick existen | No probado con destino real. |
| No filler | PASS | Preview/dry-run y filtros bloquean picks sin cuota/seleccion/calidad | Produccion admin no accesible. |
| Dedupe | PARTIAL | Contrato local PASS; productivo bloqueado por acceso | No se pudo comprobar cola real. |
| Retry | PASS | Retry de HTML a texto plano y max attempts por item | No se provoco error real. |
| Ultimo error | BLOCKED_BY_ACCESS | Disponible via snapshot admin | Requiere admin read-only. |
| Ultima entrega | BLOCKED_BY_ACCESS | Disponible via snapshot admin | Requiere admin read-only. |
| Logs Render | BLOCKED_BY_ACCESS | No hay `RENDER_API_KEY` ni acceso dashboard en entorno local | Requiere acceso Render read-only. |
| Permisos destino | BLOCKED_BY_ACCESS | No hay token local para getChat/getChatMember | Requiere token disponible o endpoint seguro. |

## Gate 3 QA ejecutada

- Runtime production read-only: PASS.
- Health production read-only: PASS.
- Endpoints admin sin sesion: PASS como proteccion 403/302.
- Tests Telegram locales sin secretos: PASS 8/8.
- Check V744 Telegram: PASS.
- Check V887 QUEUE_SKIPPED: PASS.
- Check V889 premium picks: incompatibilidad legacy de version literal, no regresion Telegram.
- Jinja parse: PASS.
- Imports/rutas: PASS.
- Privacy/Secret Guard: PASS, 0 secretos confirmados.
- Dedupe/retry/rate-limit simulation: PASS.

## Bloqueo restante exacto

Falta acceso real controlado a una de estas vias:

1. variables locales `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` mas acceso Render logs read-only; o
2. sesion admin read-only que permita consultar `/api/admin/telegram/status`, `/api/admin/telegram/dry-run`, `/api/admin/telegram/preview-next`, `/api/admin/telegram/dedupe-status`, `/api/admin/telegram/environment-audit`; y acceso Render logs; o
3. una herramienta segura de plataforma que ejecute getMe/getChat/getChatMember y exponga solo evidencia enmascarada.

## Resultado

Telegram queda BLOCKED para PASS productivo. No es un fallo confirmado de Telegram; es falta de acceso suficiente para completar la certificacion real autorizada.
