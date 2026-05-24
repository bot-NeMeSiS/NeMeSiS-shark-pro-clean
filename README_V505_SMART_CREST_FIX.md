# NeMeSiS SHARK PRO V505 - Smart Crest Fix

V505 soluciona el sistema de escudos dentro del core limpio.

## Incluye
- Resolucion de equipos por alias.
- Cache SQLite en tabla `teams`.
- Soporte para `THESPORTSDB_KEY` o `THESPORTSDB_API_KEY`.
- Endpoint `/api/team/resolve?team=Real%20Madrid&refresh=1`.
- Endpoint `/api/teams`.
- Endpoint `/api/import-teams`.
- Endpoint `/api/crest-diagnostics`.
- Fallback SVG premium propio en `/team-crest.svg?name=Equipo`.
- Calendario y Live Center muestran imagen de escudo si existe, o fallback visual si no.

## Render
En Render, configura una de estas variables si quieres resolver escudos externos:

- `THESPORTSDB_KEY`
- `THESPORTSDB_API_KEY`

Si no hay clave, la app sigue funcionando con escudos fallback premium y con logos cargados manualmente desde `/admin/import-center`.

## Legalidad
No scraping ilegal. Los escudos deben venir de API permitida, carga manual autorizada o fallback generado por la app.
