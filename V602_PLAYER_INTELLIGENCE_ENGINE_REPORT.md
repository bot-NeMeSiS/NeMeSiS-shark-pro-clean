# V602 — Player Intelligence Engine

## Objetivo

Exprimir mejor API-Football Pro y el warehouse actual para que SHARK tenga lectura de jugadores, alineaciones, bajas, dudas y señales de impacto.

## Implementado

- Nuevo motor: `engines/player_intelligence_engine.py`.
- Nuevas tablas SQLite seguras:
  - `player_profiles`
  - `player_availability_history`
  - `player_match_stat_snapshots`
  - `player_team_impact_signals`
  - `player_intelligence_runs`
- Importación desde datos ya guardados por V601:
  - `api_football_lineups_deep`
  - `api_football_injuries_history`
- Generación de señales propias:
  - bajas detectadas
  - impacto estimado
  - profundidad de alineación
- Integración en `seed_core()`.
- Integración en scheduler `warehouse`.
- Integración en `/admin/data-center`.
- Endpoints de control.

## Legalidad

No revende datos crudos. Guarda datos autorizados para operar NeMeSiS, alimentar SHARK y crear señales derivadas propias.

## QA

- `python -m compileall app.py engines database_manager.py` OK.
- Actualización sin `.git`.
- Actualización sin `__pycache__`.
- No requiere cambios en login, membresías, Telegram ni Render.

## Próximo paso recomendado

V603 — Advanced Team Intelligence: usar señales de jugadores + forma + ratings + estadísticas para mejorar ataque/defensa, localía y momentum predictivo.
