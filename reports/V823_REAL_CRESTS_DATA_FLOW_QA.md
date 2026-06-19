# V823 Real Crests Data Flow QA

## Objetivo

Confirmar que el pulido visual V823 usa la capa de escudos V820/V821/V822 sin reabrir el riesgo de 502.

## Estado verificado

- `/asset/team-logo/<team_key>` existe.
- `/asset/league-logo/<league_key>` existe.
- `/team-crest.svg` existe.
- Las rutas de logos siguen tratadas como rutas ligeras.
- El motor `engines/crest_engine.py` no hace llamadas externas durante render.
- Los fallbacks SVG siguen disponibles.
- `v822_runtime_stability_snapshot()` expone conteos ligeros de cache de logos.

## Politica mantenida

- No descargar logos al renderizar.
- No migrar DB desde rutas de imagen.
- No escribir SQLite durante render de tarjetas.
- Fallback premium si falta logo, tabla, DB o hay lock.

## Resultado

`tools/check_v823_real_crests_render_safe.py` paso correctamente.
