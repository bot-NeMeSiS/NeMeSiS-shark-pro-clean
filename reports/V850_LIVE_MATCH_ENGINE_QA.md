# V850 Live Match Engine QA

Se creo `engines/live_match_experience_engine.py`.

Funciones cubiertas:

- `get_live_matches_cached()`
- `get_live_matches_from_api_sports_safe(dry_run=False)`
- `normalize_live_match(raw)`
- `get_match_status_label(match)`
- `get_match_minute_label(match)`
- `get_score_label(match)`
- `build_live_card_payload(match)`
- `explain_live_data_state()`
- `should_refresh_live_cache()`
- `live_cache_summary()`

Politica:

- Cache-first.
- Sin llamadas API por render.
- Dry-run seguro.
- Madrid Time preservado en capas superiores.
- Sin datos inventados.
- Fallback premium si falta proveedor.
