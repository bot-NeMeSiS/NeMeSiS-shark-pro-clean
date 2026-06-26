# V847 Matches Live API-SPORTS Integration QA

Pantallas revisadas:

- `/app`
- `/partidos`
- `/calendar`
- `/live`
- `/directo`
- `/match/`

Estado:

- Live usa `sync_api_football_live_tracker(DB_PATH, force=...)`.
- Match detail usa `sync_api_football_fixture_detail(DB_PATH, match_id, force=...)`.
- V818 master tick conserva `sync_api_football_match_window`.
- La app mantiene fallback a datos existentes/cache si API-SPORTS falla o no está configurada.

Reglas preservadas:

- No inventar minuto, resultado, evento ni estadística.
- Pasado sin marcador = Resultado pendiente.
- Falta proveedor = Esperando proveedor.
- Sin datos = Sin datos reales.
