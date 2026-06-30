# V863 Real Security QA

## Certificado en Render real

- APIs admin sin sesión: 403.
- Cron sin secret: 403.
- Rutas admin sin sesión: 302 a login.
- Runtime no muestra claves.
- `automation_secret_configured`: `true` sin exponer valor.
- `telegram_configured`: `true` sin exponer token.
- `api_sports_configured`: `true` sin exponer key.
- `the_odds_configured`: `true` sin exponer key.

## Pendiente

Prueba autenticada admin y pagos test requieren credenciales/keys seguras no disponibles.
