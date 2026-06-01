# NeMeSiS SHARK PRO — V527 MATCH DETAIL PRO + SHARK CONTEXT AI

Build limpia Render-ready basada en V526 con el salto de detalle de partido y SHARK contextual.

## Incluye

- Pantalla individual de partido `/match/<id>`.
- API de detalle `/api/matches/<id>/detail`.
- API de timeline `/api/matches/<id>/timeline`.
- API de estadísticas `/api/matches/<id>/statistics`.
- Picks relacionados dentro del partido.
- Estado visual del partido: Próximo, En directo, Descanso, Finalizado o Suspendido.
- Escudos/fallback premium.
- SHARK IA contextual para partido, favoritos y picks.
- Mantiene favoritos, resultados, picks, combis, live, calendario y separación cliente/admin.

## QA

- `app.py` compila OK.
- Engines compilan OK.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs antiguos.

## Render

Mantener variables habituales:

```txt
DB_PATH=/data/database.db
SECRET_KEY=...
THESPORTSDB_API_KEY=...
THESPORTSDB_KEY=...
THE_ODDS_API_KEY=...
ENABLE_LIVE_API=true
ENABLE_ODDS_API=true
```
