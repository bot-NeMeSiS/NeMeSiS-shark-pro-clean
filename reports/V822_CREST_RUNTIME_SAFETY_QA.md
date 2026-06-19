# V822 Crest Runtime Safety QA

## Validado

- `safe_get_team_logo` y `safe_get_league_logo` devuelven fallback sin DB.
- `safe_crest_context` centraliza fallback seguro.
- `fallback_crest_svg` conserva `/team-crest.svg`.
- `ensure_logo_tables_once` no propaga errores.
- No hay descargas externas de escudos en runtime.
- `/asset/team-logo/test` y `/asset/league-logo/test` deben responder sin 500.

## Politica

Los escudos reales se usan si existen en datos/cache. Si no existen, se usa fallback premium. No se inventan escudos oficiales.

## Validacion ejecutada

- `tools/check_v822_crest_runtime_safety.py` OK.
- `/asset/team-logo/test`: 302 seguro.
- `/asset/league-logo/test`: 302 seguro.
- `/team-crest.svg?name=Costa+de+Marfil`: 200.
- Fallback sin DB medido por check: inferior a 100 ms.
