# V938 Automation Secret Transport Hardening

## Estado

- Nuevo Cron V938: **CONFIRMADO / HEADER ONLY**.
- Endpoints históricos: **REQUIERE REVISIÓN / COMPATIBILIDAD DEPRECADA**.

`POST /api/automation/operations-center/run` solo acepta `X-Automation-Secret` o `X-CRON-SECRET`. El mismo valor en query string devuelve 403. La respuesta nunca refleja el secreto.

Los endpoints Cron heredados siguen usando el helper compatible de V937 para no romper Render Cron sin una migración autorizada. Se marca como deuda: migrar cada job a headers, certificarlo y retirar query/form/JSON en una ventana operativa controlada. V938 no cambia silenciosamente jobs reales.
