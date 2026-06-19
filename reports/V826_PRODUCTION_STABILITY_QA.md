# V826 Production Stability QA

## Protecciones preservadas

- V818 master tick y health-check.
- V819 dedupe.
- V820 crest routes.
- V821 502 hotfix.
- V822 runtime stability.
- V823/V824 visual safety.
- V825 SHARK identity.
- DB_PATH sin cambios.
- Madrid Time sin cambios.
- Telegram automático sin cambios funcionales.

## Cambios de bajo riesgo

- Versionado.
- Marcadores data-v826-template.
- CSS final additive.
- Corrección de textos corruptos visibles.
- Herramientas de check V826.

## No realizado

- No se cambió lógica de picks.
- No se cambió scheduler.
- No se cambió Telegram.
- No se cambió base de datos.

## Validación ejecutada

- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines tools`: OK.
- Parse Jinja de 29 templates: OK.
- Checks V818, V819, V820, V821, V822, V823, V824, V825: OK.
- Checks V826 nuevos: OK.
- Smoke Flask con DB temporal: OK, sin 500 ni incidencia controlada.

## Corrección adicional detectada en V826

En una DB totalmente nueva, `/api/runtime-version` podía fallar si `automation_state` aún no existía. Se corrigió `v822_runtime_stability_snapshot()` para que lea `last_master_tick` con fallback seguro y registre warning interno en vez de lanzar 500. No inicializa la app ni escribe en SQLite durante runtime.

## Rutas smoke probadas

`/`, `/cliente-login`, `/registro`, `/app`, `/calendar`, `/partidos`, `/live`, `/directo`, `/picks`, `/shark`, `/shark-core`, `/profile`, `/telegram`, `/support`, `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`, `/api/runtime-version`, `/asset/team-logo/test`, `/asset/league-logo/test`, `/team-crest.svg?name=Costa+de+Marfil`, `/api/automation/master-tick`, `/api/automation/master-tick?secret=...&dry_run=1`, `/api/automation/health-check?secret=...`, `/admin/dashboard`, `/admin/map`, `/admin/daily-automation`, `/admin/automation-os`, `/admin/data-center`, `/admin/telegram/command-center`.
