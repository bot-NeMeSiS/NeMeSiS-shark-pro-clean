# V891/V893 Security And Automation QA

## Endpoints admin

Los endpoints `/api/admin/autonomous-sentinel/*` quedan protegidos por sesion admin. Sin sesion deben devolver 403.

## Cron

Endpoint protegido:

- `/api/automation/autonomous-sentinel/run`

Sin `AUTOMATION_SECRET` debe devolver 403. Con secret local y `dry_run=1` debe devolver 200 sin ejecutar acciones peligrosas.

## Datos y secretos

El worker no lee ni expone tokens, claves API, `TELEGRAM_BOT_TOKEN`, `AUTOMATION_SECRET` ni datos de pago.

## Datos reales

No inventa partidos, picks, cuotas, resultados, escudos, usuarios, pagos ni envios Telegram.
