# V821 502 Root Cause Audit

Version: `V821_PRODUCTION_502_CRESTS_RUNTIME_HOTFIX`

## Ruta afectada

Produccion reporto 502/timeouts despues de V820 en rutas cliente como `/cliente-login`, `/app` y navegacion relacionada. En local no aparecio traceback Python directo, pero la auditoria del flujo V820 detecto dos riesgos de produccion compatibles con 502 en Render:

- rutas de imagen `/asset/team-logo/<team_key>` y `/asset/league-logo/<league_key>` no estaban marcadas como ligeras y podian disparar `initialize_once()`;
- `apply_team_identities_to_match()` escribia en cache SQLite de logos durante el render de listas de partidos.

## Error real probable

Timeout/lock de worker por trabajo de DB innecesario en tiempo de render:

- migracion/creacion de tablas desde rutas de asset;
- conexiones SQLite con timeout largo para servir logos;
- escrituras repetidas de cache por cada partido/tarjeta;
- multiples requests de imagen disparadas por una sola pagina.

## Archivo afectado

- `app.py`
- `engines/crest_engine.py`

## Fix aplicado

- `/asset/team-logo/<team_key>`, `/asset/league-logo/<league_key>` y `/team-crest.svg` quedan como endpoints ligeros.
- Las rutas `/asset/*` ya no ejecutan `ensure_crest_logo_schema()` ni migraciones.
- Las rutas `/asset/*` usan conexion SQLite directa con timeout corto y fallback inmediato.
- `apply_team_identities_to_match()` deja de escribir en cache durante render.
- El motor `crest_engine` añade helpers seguros que siempre devuelven logo real o fallback local.
- `/api/runtime-version` reporta `last_502_hotfix=true`, `crest_engine_loaded`, `logo_routes_ok` y `logo_cache_tables_ok`.

## Resultado esperado

Las paginas cliente pueden cargar aunque falle SQLite, falten tablas de logos o no existan escudos reales. Los logos nunca deben tumbar una ruta HTML.
