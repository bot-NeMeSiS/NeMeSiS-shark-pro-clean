# V939 Company Intelligence Cron QA

Endpoint: `POST /api/automation/company-intelligence/run`.

- Sin header: 403.
- Secreto en query string: 403.
- Header de test correcto en DB temporal: 200.
- Secreto devuelto: no.
- Llamadas externas: 0.
- Escritura DB de produccion: no.
- Telegram enviado: no.
- Pago ejecutado: no.
- Pesos modificados: no.
- Push/deploy: no.
- Efecto permitido: guardar snapshot interno saneado.

Render Cron real: `NOT_CERTIFIED` porque no se ha desplegado V939.
