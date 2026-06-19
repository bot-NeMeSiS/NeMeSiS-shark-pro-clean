# V820 Crests Logos Real Data QA

## Sistema central

Creado/reforzado:

- `engines/crest_engine.py`
- `team_logo_cache`
- `league_logo_cache`
- `/asset/team-logo/<team_key>`
- `/asset/league-logo/<league_key>`

## Pantallas cubiertas

Todas las pantallas que usan `partials/team_identity.html` y el filtro `team_identity` pasan por el resolver central:

- Home
- App cliente
- Calendar / Partidos
- Live / Directo
- Picks
- Match Detail
- Favoritos cuando renderiza partidos
- Admin cuando usa identidades de equipos

## Reglas

- Logo real si ya viene de proveedor o cache.
- No se inventan logos.
- Fallback SVG solo como ultimo recurso.
- No se bloquea una pagina por imagen externa.
- Si una imagen falla, el fallback visible queda en la card.

## Validacion esperada

`tools/check_v820_real_crests.py` valida motor, tablas, resolver, fallback y partial.
