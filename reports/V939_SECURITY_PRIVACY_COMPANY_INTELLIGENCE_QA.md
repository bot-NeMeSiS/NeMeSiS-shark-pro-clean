# V939 Security and Privacy QA

## Controles V939

- APIs admin: 403 sin sesion.
- POST admin: CSRF obligatorio.
- Cron: header `X-Automation-Secret`; query string rechazada.
- Memoria: redaccion de campos sensibles y limites de retencion.
- Analytics: salida agregada, sin PII ni fingerprinting.
- Motores nuevos: sin rutas de red, Stripe, Telegram, Git o Render.
- Recovery: simulacion sin restore.
- Experimentos sensibles: bloqueados.
- Runtime: no expone usuarios, cookies, IDs privados ni valores de entorno.

V938 Secret Guard, Telegram webhook signature, Stripe signatures e idempotencia se preservan; su certificacion real de produccion no se sustituye por estos tests locales.

Estado local: `PARTIALLY_VERIFIED`. Produccion: `NOT_CERTIFIED`.
