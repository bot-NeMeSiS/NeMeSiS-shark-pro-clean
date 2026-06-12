# V717.3 — Bet Selection Clarity

## Objetivo
Corregir las vistas donde seguía apareciendo `Local` o `Visitante` como selección de apuesta, sustituyéndolo por una instrucción clara y accionable para el cliente.

## Problema detectado
En pantallas como SHARK / Picks explicados se mostraban selecciones genéricas:

- Local
- Visitante
- Home
- Away
- 1
- 2

Esto no es suficientemente claro para un cliente, porque obliga a deducir qué equipo corresponde.

## Corrección aplicada
Se añadió un helper central en `engines/spanish_localization_engine.py`:

- `spanish_pick_selection_name(...)`

Ahora convierte:

- `Local`, `Home`, `1` → `Gana [equipo local]`
- `Visitante`, `Away`, `2` → `Gana [equipo visitante]`
- `Empate`, `Draw`, `X` → `Empate`
- `Over 2.5` → `Más de 2.5 goles`
- `Under 2.5` → `Menos de 2.5 goles`
- `BTTS Yes` → `Ambos equipos marcan: Sí`
- `BTTS No` → `Ambos equipos marcan: No`
- `1X` → `[equipo local] o empate`
- `X2` → `[equipo visitante] o empate`
- nombres directos de equipo → `Gana [equipo]`

## Archivos principales tocados

- `engines/spanish_localization_engine.py`
- `app.py`
- `templates/shark.html`
- `templates/picks.html`
- `templates/sports_hub.html`
- `templates/combis.html`
- `templates/match_detail.html`
- `templates/client_overview.html`
- `templates/favorites.html`
- `templates/profile.html`
- `templates/daily_briefing.html`
- `templates/smart_dashboard.html`
- `templates/team_detail.html`
- `templates/unified_intelligence_hub.html`
- `templates/discovery.html`
- `templates/admin_picks.html`
- `VERSION.txt`

## Resultado esperado
Donde antes se veía:

`Visitante`  
`Inglaterra vs Croacia`

Ahora debe verse:

`Gana Croacia`  
`Inglaterra vs Croacia`

Donde antes se veía:

`Local`  
`Canadá vs Bosnia y Herzegovina`

Ahora debe verse:

`Gana Canadá`  
`Canadá vs Bosnia y Herzegovina`

## Validación local

- `python -m py_compile app.py` OK
- `python -m py_compile engines/spanish_localization_engine.py` OK
- `python -m compileall -q templates app.py engines` OK

## Notas
No se toca Render, Telegram, Cron, DB_PATH ni secretos. Esta versión es una corrección de claridad de picks y experiencia cliente.
