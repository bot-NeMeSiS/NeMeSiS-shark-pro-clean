# V836 Production Stability QA

## Objetivo

Mantener intactas las bases estables mientras se aplica QA visual autónomo.

## Preservado

- Render deploy.
- DB_PATH.
- Madrid Time.
- Telegram automático.
- Render Cron.
- Master tick.
- Health-check.
- API-Football.
- The Odds API.
- Login cliente/admin.
- Usuarios, sesiones, membresías y pagos.
- Sistema ligero de escudos.
- Protección 500/502/database locked.

## Checks esperados

- `py_compile app.py`
- `compileall app.py engines tools`
- parse Jinja templates
- `tools/check_madrid_times.py`
- checks V836
- smoke Flask
- audit ZIP con `forbidden_count=0`

## Resultado V836

- `py_compile app.py`: OK.
- `compileall app.py engines tools`: OK.
- Parse Jinja: OK en 151 templates.
- Madrid Time: OK.
- Checks V836 runtime/mobile/desktop/routes/data/compatibility: OK.
- Smoke Flask: OK, sin 500 ni incidencia controlada.
- `/api/automation/master-tick` sin secret: 403.
- `/api/automation/master-tick` con secret y `dry_run=1`: 200.
- `/api/automation/health-check` con secret: 200.
- ZIP auditado: OK.
- `forbidden_count`: 0.
- ZIP final: `release_output\NeMeSiS_SHARK_PRO_V836_AUTONOMOUS_REFERENCE_VISUAL_REVIEW_FINAL_QA_RENDER_READY.zip`.

Nota: se generaron DB temporales de prueba en `data/`; el ZIP limpio las excluye por política de release.
