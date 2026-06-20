# V832 V818 To Latest Compatibility QA

## Compatibilidad

V832 conserva marcadores y funciones críticas desde V818 hasta V830, y añade V832 encima como capa de experiencia visual y workflow.

## Críticos conservados

- `/api/automation/master-tick`
- `/api/automation/health-check`
- rutas de escudos ligeras
- DB_PATH `/data/database.db`
- Telegram automático
- Render Cron
- pagos/membresías
- rutas cliente/admin

## Check

`tools/check_v832_v818_to_latest_compatibility.py` valida runtime, CSS, shell y marcadores principales.
