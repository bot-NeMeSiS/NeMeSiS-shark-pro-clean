# V873 logo/crest cache zero QA

## Runtime real

- `team_logo_cache_count=0`.
- `league_logo_cache_count=0`.
- `logo_cache_tables_ok=true`.
- `logo_routes_ok=true`.
- `crest_engine_loaded=true`.

## Interpretación

La infraestructura de logos existe, pero la cache real de producción no contiene entradas. No se puede afirmar que haya logos reales cacheados.

## Corrección V873

- Runtime local añade `logo_cache_state` y `logo_cache_note`.
- CSS V873 refuerza fallback premium cuando `data-real-logo=false` o imagen falla.
- No se descargan logos durante render.
- No se inventan escudos oficiales.

## Siguiente paso seguro

Ejecutar un sync/dry-run de logos desde admin/cron si existe autorización. Si se pobla cache, validar recuentos en runtime y cards reales.
