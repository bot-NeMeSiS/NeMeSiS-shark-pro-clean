# V852 Escudos, Logos y Fallback

## Revisado
- `crest_logo_experience_engine.py`.
- `partials/team_identity.html`.
- `live.html`, `picks.html`, `match_detail.html`.

## Resultado
V852 no cambia el motor de escudos para no romper V850. Sí valida que las pantallas críticas siguen usando `crest()` o `team_identity`.

## Reglas preservadas
- No inventar escudos oficiales.
- No descargar logos durante render.
- Fallback premium si falta logo.
