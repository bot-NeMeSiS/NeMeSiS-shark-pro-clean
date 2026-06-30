# V867 real Sentinel workflow production QA

## Producción real sin sesión/secret
Base: `https://bot-apuestas-crgf.onrender.com`.

| Endpoint | Estado esperado | Estado observado |
| --- | ---: | ---: |
| `/api/admin/continuous-sentinel/summary` | 403 | 403 |
| `/api/admin/sentinel-workflow/summary` | 403 | 403 |
| `/api/admin/sentinel-workflow/tasks` | 403 | 403 |
| `/api/automation/continuous-sentinel/run` | 403 | 403 |
| `/api/automation/master-tick` | 403 | 403 |

## No probado
- No se probó `dry_run=1` con `AUTOMATION_SECRET`, porque no se deben exponer ni pedir secretos en esta tarea.
- No se envió Telegram real.
- No se ejecutaron syncs caros.

## Resultado
Sentinel/admin workflow y cron mantienen protección correcta sin sesión ni secret.
