# V821 Login/App Smoke QA

## Rutas objetivo

- `/`
- `/cliente-login`
- `/app`
- `/calendar`
- `/partidos`
- `/live`
- `/directo`
- `/picks`
- `/shark`
- `/profile`
- `/telegram`
- `/support`
- `/api/runtime-version`
- `/api/automation/master-tick`
- `/asset/team-logo/test`
- `/asset/league-logo/test`
- `/team-crest.svg?name=Costa+de+Marfil`
- `/admin/dashboard`
- `/admin/daily-automation`

## Resultado ejecutado

Validacion ejecutada con Flask test client y DB temporal `data/v821_smoke.db`.

- `/`: 200
- `/cliente-login`: 200
- `POST /cliente-login` sin CSRF real: 403 esperado, sin 500
- `/app`: 200
- `/calendar`: 200
- `/partidos`: 200
- `/live`: 200
- `/directo`: 200
- `/picks`: 200
- `/shark`: 200
- `/profile`: 200
- `/telegram`: 200
- `/support`: 200
- `/api/runtime-version`: 200 y version V821
- `/api/automation/master-tick` sin secret: 403 esperado
- `/api/automation/master-tick` con secret: 200
- `/api/automation/health-check` con secret: 200
- `/asset/team-logo/test`: 302 a fallback/logo
- `/asset/league-logo/test`: 302 a fallback/logo
- `/team-crest.svg?name=Costa+de+Marfil`: 200
- `/admin/dashboard`: 200 con sesion admin simulada
- `/admin/daily-automation`: 200 con sesion admin simulada
- `/admin/data-center`: 200 con sesion admin simulada
- `/admin/telegram/command-center`: 200 con sesion admin simulada

No hubo 500 ni "Incidencia controlada" en rutas probadas.

## Nota

La prueba no usa APIs externas ni descarga logos; valida que el runtime local de Flask no se bloquea por crests/logos.
