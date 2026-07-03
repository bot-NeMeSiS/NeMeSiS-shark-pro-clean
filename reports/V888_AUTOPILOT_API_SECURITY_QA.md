# V888 AutoPilot API Security QA

## APIs admin

- `GET /api/admin/sentinel-autopilot/summary`
- `POST /api/admin/sentinel-autopilot/run`
- `GET /api/admin/sentinel-autopilot/issues`
- `GET /api/admin/sentinel-autopilot/tasks`
- `POST /api/admin/sentinel-autopilot/generate-prompt`
- `POST /api/admin/sentinel-autopilot/mark-resolved`

Todas requieren sesion admin. Sin sesion deben devolver 403.

## Sin secretos

Las APIs no exponen `TELEGRAM_BOT_TOKEN`, `AUTOMATION_SECRET`, `OPENAI_API_KEY`, `STRIPE_SECRET_KEY` ni claves de proveedores.
