# V828 Production Stability QA

## Reglas preservadas

- No se cambia `DB_PATH`.
- No se toca Render Cron.
- No se toca Telegram automático.
- No se modifica master tick V818.
- No se toca Madrid Time.
- No se introducen descargas runtime de logos.
- No se escriben datos desde rutas de imagen.

## Validación prevista

- `python -m py_compile app.py`
- `python -m compileall app.py engines tools`
- Parse Jinja templates.
- Checks V818-V827.
- Checks V828.
- Smoke Flask de rutas cliente/admin/API.
- Build ZIP limpio.
- Audit ZIP con `forbidden_count=0`.

## Resultado ejecutado

- `py_compile app.py`: OK.
- `compileall app.py engines tools`: OK.
- Parse Jinja templates: 144 templates OK.
- `check_madrid_times.py`: OK.
- Checks V818-V827: OK tras reconocer V828 como runtime actual preservando marcas históricas.
- Checks V828 nuevos: OK.
- Smoke Flask: OK, sin 500 ni incidencia controlada.

Rutas smoke probadas:

- `/`: 200.
- `/cliente-login`: 200.
- `/registro`: 200.
- `/app`: 302 por login requerido.
- `/calendar`: 200.
- `/partidos`: 200.
- `/live`: 200.
- `/directo`: 200.
- `/picks`: 200.
- `/shark`: 200.
- `/shark-core`: 302 por protección.
- `/profile`: 302 por login requerido.
- `/telegram`: 302 por login requerido.
- `/support`: 200.
- `/favorites`: 302 por login requerido.
- `/track-record`: 200.
- `/combis`: 200.
- `/mercados`: 200.
- `/highlights`: 200.
- `/api/runtime-version`: 200.
- `/team-crest.svg?name=Costa+de+Marfil`: 200.
- `/api/automation/master-tick`: 403 sin secret.
- `/api/automation/master-tick?secret=...&dry_run=1`: 200.
- `/api/automation/health-check?secret=...`: 200.
- Rutas admin principales: 302 por protección, sin incidencia.

## Riesgos

La app conserva muchas capas antiguas por compatibilidad. V828 las neutraliza visualmente donde molestan, pero no hace una purga destructiva.
