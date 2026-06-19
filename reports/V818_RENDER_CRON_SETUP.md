# V818 Render Cron Setup

Endpoint principal:

`GET https://bot-apuestas-crgf.onrender.com/api/automation/master-tick?secret=AUTOMATION_SECRET`

Frecuencia recomendada:

- Cada 15 minutos si Render lo permite.
- Si el plan no permite 15 minutos, usar cada hora y mantener los endpoints especificos actuales.

Endpoints legacy conservados:

- `/api/automation/telegram/tick`
- `/api/automation/highlights/sync`
- `/api/automation/data-backup/run`

El master tick decide por hora Madrid que jobs toca ejecutar. El secreto se valida con `AUTOMATION_SECRET`; no debe escribirse en logs ni reportes.
