# V814 Match Lifecycle and Live Data QA

## Reglas certificadas

- Kickoff futuro: `Próximo`.
- Kickoff empezado sin marcador: `En juego · actualizando`.
- Live API con minuto: `En directo`.
- Final API con resultado: `Finalizado`.
- Partido pasado sin score: `Resultado pendiente`.
- Partido de madrugada ya pasado: `Resultado pendiente`.

## Funciones revisadas

- `match_kickoff_madrid_dt`
- `match_elapsed_minutes`
- `has_real_match_score`
- `match_is_stale_without_result`
- `match_is_already_kicked_off`
- `canonical_match_status`
- `client_match_display_context`
- `get_results_matches`
- `grouped_match_calendar`
- `calendar_experience_data`

## API-Football / Live

La app ya integra `api_football_live_tracker_engine.py` y las plantillas `live.html` / `match_detail.html` muestran eventos, estadísticas, ataques peligrosos, córners, posesión, tiros y estado solo si el proveedor los trae. No se inventan marcador, pelota, ataques ni eventos.

## Check añadido

`tools/check_v814_full_ecosystem_reconciliation.py` valida seis casos de lifecycle, incluyendo partido nocturno ya pasado.
