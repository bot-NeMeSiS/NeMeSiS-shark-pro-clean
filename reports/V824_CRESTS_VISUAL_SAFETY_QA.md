# V824 Crests Visual Safety QA

## Validacion

- Rutas `/asset/team-logo/<team_key>`, `/asset/league-logo/<league_key>` y `/team-crest.svg` preservadas.
- Timeout corto de lectura SQLite preservado.
- Sin descargas externas en `engines/crest_engine.py`.
- Fallback SVG preservado.
- CSS V824 mejora tamanos, bordes y sombras de escudos.

## Resultado

`tools/check_v824_crests_visual_safety.py` paso correctamente.

## Politica mantenida

- No escrituras SQLite durante render.
- No migraciones desde rutas de imagen.
- No logos inventados.
- Fallback inmediato si falta dato real.
