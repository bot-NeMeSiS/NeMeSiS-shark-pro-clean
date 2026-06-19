# V825 Production Stability Regression QA

## Validaciones ejecutadas

- `py_compile app.py`: OK.
- `compileall app.py engines tools`: OK.
- Parse Jinja templates principales: OK.
- `tools/check_madrid_times.py`: OK.
- Checks V818, V819, V820, V821, V822, V823, V824: OK.
- Checks V825: OK.
- Smoke Flask con DB temporal:
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
  - rutas admin objetivo: 302 a login sin sesion, sin 500.

## Politica preservada

- No escrituras SQLite durante render.
- No migraciones desde rutas de imagen.
- No descargas externas runtime.
- DB_PATH no cambiado.
- V818-V824 preservados.
