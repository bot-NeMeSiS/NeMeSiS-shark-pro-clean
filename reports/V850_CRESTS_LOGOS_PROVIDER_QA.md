# V850 Crests Logos Provider QA

Se creo `engines/crest_logo_experience_engine.py`.

Funciones cubiertas:

- `get_team_logo()`
- `get_league_logo()`
- `normalize_logo_url()`
- `cache_logo_reference()`
- `build_team_crest_payload()`
- `build_league_logo_payload()`
- `get_logo_fallback()`
- `explain_logo_state()`

Reglas mantenidas:

- No se inventan escudos oficiales.
- No se descargan logos durante render.
- No se escriben archivos pesados.
- Si API-SPORTS aporta logo, se puede usar referencia cacheada.
- Si falta logo real, se usa fallback premium local.
