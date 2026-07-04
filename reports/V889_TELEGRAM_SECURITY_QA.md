# QA seguridad Telegram V889

Validaciones:
- No se exponen `TELEGRAM_BOT_TOKEN`.
- No se expone `AUTOMATION_SECRET`.
- Admin APIs bloquean sin sesion.
- Cron bloquea sin secret.
- Dry-run no envia.
- No hay trazas publicas de debug.
- No se crean picks falsos.
- No se crean cuotas falsas.
