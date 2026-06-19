# V824 Production Stability Regression QA

## Validaciones esperadas

- `py_compile app.py`: ejecutado OK.
- `compileall app.py engines tools`: OK.
- `tools/check_madrid_times.py`: OK.
- Checks V824: ejecutados OK.
- Checks V818/V819/V820/V821/V822/V823 compatibles con V824: OK.
- Parse Jinja de templates principales: OK.
- Smoke Flask con DB temporal local:
  - `/`: 200
  - `/cliente-login`: 200
  - `/app`: 302 login requerido, sin 500
  - `/calendar`: 200
  - `/partidos`: 200
  - `/live`: 200
  - `/directo`: 200
  - `/picks`: 200
  - `/shark`: 200
  - `/profile`: 302 login requerido, sin 500
  - `/telegram`: 302 login requerido, sin 500
  - `/support`: 200
  - `/api/runtime-version`: 200
  - `/asset/team-logo/test`: 302 fallback SVG
  - `/asset/league-logo/test`: 302 fallback SVG
  - `/team-crest.svg?name=Costa+de+Marfil`: 200
  - `/api/automation/master-tick`: 403 sin secret
  - `/api/automation/master-tick?secret=...&dry_run=1`: 200
  - `/api/automation/health-check?secret=...`: 200
  - rutas admin objetivo: 302 a login si no hay sesion admin, sin 500.

## Garantias preservadas

- V818 master tick.
- V819 dedup.
- V820 crests.
- V821 hotfix 502.
- V822 runtime stability.
- V823 visual/crest polish.
- DB_PATH sigue apuntando a `/data/database.db`.

## Politica anti-regresion

- No escrituras SQLite durante render.
- No descargas runtime de logos.
- Asset routes ligeras.
- Master tick protegido por secret.

## Nota local

Para smoke Flask en Windows puede ser necesario usar DB temporal porque `/data` no es escribible localmente. Esto no cambia el comportamiento Render.
