# V926 Sports Desktop Boards QA

## Calendario

- Filtros y busqueda suben antes de la lista real.
- Layout hibrido con contenido principal y panel lateral de 310 px.
- Hora, competicion, equipos, estado y resultado siguen usando el contexto existente.

## Directo

- Filtros `En vivo / Proximos / Finalizados` aparecen antes del board.
- Estado del proveedor visible sin forzar llamadas de red.
- Marcador y minuto solo se muestran si existen en los datos.

## Contextos seguros

`get_safe_sports_calendar_context`, `get_safe_live_context`, `get_safe_picks_context` y `get_safe_odds_context` exponen `source`, `has_real_data`, `last_sync`, `provider_status`, `cache_status`, `safe_message` y `no_render_api_call=true` segun corresponda.

