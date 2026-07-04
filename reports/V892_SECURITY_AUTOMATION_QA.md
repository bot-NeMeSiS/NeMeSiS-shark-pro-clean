# V892/V894 Security Automation QA

## Admin

Todos los endpoints `/api/admin/autonomous-company-sentinel/*` requieren sesion admin y deben devolver 403 sin sesion.

## Cron

`/api/automation/autonomous-company-sentinel/run` requiere `AUTOMATION_SECRET`.

## Secretos

No se muestran:

- TELEGRAM_BOT_TOKEN
- AUTOMATION_SECRET
- OPENAI_API_KEY
- STRIPE_SECRET_KEY
- API keys
- cookies
- passwords

## Acciones prohibidas

No deploy, no push, no Telegram real, no pagos reales, no DB real, no datos inventados.
