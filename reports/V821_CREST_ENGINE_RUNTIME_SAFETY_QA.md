# V821 Crest Engine Runtime Safety QA

## Objetivo

Mantener escudos reales cuando existan, pero impedir que logos, cache SQLite o migraciones causen 500/502.

## Cambios verificados

- `safe_get_team_logo(...)` devuelve payload valido aunque no haya conexion DB.
- `safe_get_league_logo(...)` devuelve fallback local si falta cache o tabla.
- `safe_crest_context(...)` centraliza fallback seguro.
- `fallback_crest_svg(...)` conserva `/team-crest.svg`.
- `ensure_logo_tables_once(...)` no propaga errores de SQLite.
- No hay `urlopen`, `requests` ni descarga externa en `engines/crest_engine.py`.
- URLs peligrosas se descartan con `safe_logo_url(...)`.

## Politica runtime

- Render normal de pagina: no descarga logos.
- Rutas de asset: lectura corta o fallback.
- Migraciones: solo en inicializacion/migracion segura, no por cada imagen.
- Faltan logos: fallback premium.
- DB lock: fallback premium.

## Estado

OK para hotfix de produccion V821.
