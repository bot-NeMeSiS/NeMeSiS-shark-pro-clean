# V742 Telegram Production Runbook

## Render Cron
- Tick: `/api/automation/telegram/tick?secret=VALOR_DE_AUTOMATION_SECRET` cada 15 minutos.
- Daily: `/api/automation/daily/run?secret=VALOR_DE_AUTOMATION_SECRET` cada hora o 10:00 Europe/Madrid.
- Sin secret debe devolver 403.
- Con secret debe devolver 200 con JSON compacto.

## Diagnóstico
- Revisar `/admin/telegram/command-center`.
- Revisar `/api/admin/telegram/status` con sesión admin.
- Usar dry-run y preview antes de un test real.
- Si Telegram dice `forbidden` o `chat not found`, revisar permisos/destino del bot.
