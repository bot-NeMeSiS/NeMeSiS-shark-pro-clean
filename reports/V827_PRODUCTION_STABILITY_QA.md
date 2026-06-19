# V827 Production Stability QA

## Preservado

- V818 master tick y health-check.
- V819 dedupe.
- V820 crest routes.
- V821 502 hotfix.
- V822 runtime stability.
- V823/V824 visual safety.
- V825 SHARK identity.
- V826 full screen coverage.
- DB_PATH sin cambios.
- Madrid Time sin cambios.
- Telegram automático sin cambios funcionales.

## Cambios de estabilidad

No se añadieron escrituras SQLite en render, descargas runtime, migraciones en rutas de imagen ni procesos pesados.

## Validación ejecutada

- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines tools`: OK.
- Parse Jinja de 29 templates: OK.
- `tools/check_madrid_times.py`: OK.
- Checks V818-V827: OK.
- Smoke Flask con DB temporal: OK, sin 500 ni incidencia controlada.
- `/api/runtime-version`: 200, V827 activo, V826/V825/V824/V818 preservados.

## Smoke routes probadas

`/`, `/cliente-login`, `/registro`, `/app`, `/calendar`, `/partidos`, `/live`, `/directo`, `/picks`, `/shark`, `/shark-core`, `/profile`, `/telegram`, `/support`, `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`, `/api/runtime-version`, `/asset/team-logo/test`, `/asset/league-logo/test`, `/team-crest.svg?name=Costa+de+Marfil`, `/api/automation/master-tick`, `/api/automation/master-tick?secret=...&dry_run=1`, `/api/automation/health-check?secret=...`, `/admin/dashboard`, `/admin/map`, `/admin/daily-automation`, `/admin/automation-os`, `/admin/data-center`, `/admin/telegram/command-center`, `/admin/users`, `/admin/memberships`.
