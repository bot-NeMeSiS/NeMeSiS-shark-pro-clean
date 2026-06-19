# V819 Runtime Stability And 502 QA

## Objetivo

Confirmar que V819 no introduce trabajo pesado en arranque ni modifica flujos Render estables.

## Medidas

- `APP_VERSION` y `VERSION.txt` actualizados.
- `/api/runtime-version` extendido con V819 sin eliminar indicadores previos.
- No se toca `DB_PATH`.
- No se cambia `seed_core`, `init_db`, scheduler, Cron ni automatizaciones.
- No se modifica Render runtime ni `render.yaml`.

## Validacion esperada

- `compileall` OK.
- Smoke routes sin 500.
- Cron sin secret 403.
- Cron con secret 200.
