# V872 logos, escudos y datos visuales

## Runtime Render observado

- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `logo_cache_tables_ok`: `true`.
- `logo_routes_ok`: `true`.

## Decisión de producto

No se inventan escudos oficiales y no se descargan logos durante render. Si API-SPORTS no ha dejado cache visual, la app debe usar fallback premium con identidad SHARK y escudos genéricos.

## Riesgo

La ausencia de caché puede hacer que las cards parezcan menos ricas visualmente aunque los datos deportivos estén protegidos. El siguiente paso seguro es revisar sync/cache de logos vía cron/dry-run, no en render de pantalla.
