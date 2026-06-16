# V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION

Avance centrado en seguir acercando NeMeSiS SHARK PRO al formato de app premium de directo y calendario, usando API-Football Pro con datos reales y control de llamadas.

## Implementado

- Resumen de calidad API-Football sin gastar llamadas externas: `live_tracker_quality_summary()`.
- Nuevo endpoint cliente protegido: `/api/live-tracker/quality`.
- `/api/live-tracker/status` ahora incluye estado + calidad del tracker.
- `/live` recibe `api_football_live_quality` para enseñar cobertura real: fixtures con estadísticas, eventos, presión, ataques y ataques peligrosos.
- Cada partido enriquecido en `live_experience_engine` lleva etiqueta de calidad: marcador básico, live con señales, live avanzado o live profundo.
- Detalle de partido con línea de calidad del live tracker, evidencias reales y acceso directo a `#live-tracker`.
- CSS V805 para tablero de calidad, chips de evidencias y línea de calidad en detalle.
- Se mantiene la política: si API-Football no entrega coordenadas del balón, no se dibuja un balón exacto falso.

## Datos reales protegidos

No se inventan partidos, cuotas, picks, resultados, eventos, estadísticas, ataques peligrosos ni posición de balón. Si el feed no lo trae, la app muestra pendiente/no disponible.

## Control de API

El resumen de calidad lee la caché local; no consume créditos. Las llamadas reales siguen controladas por:

- `API_FOOTBALL_LIVE_CACHE_SECONDS`
- `API_FOOTBALL_LIVE_DETAIL_CACHE_SECONDS`
- `API_FOOTBALL_LIVE_DEEP_LIMIT`

## Archivos principales

- `engines/api_football_live_tracker_engine.py`
- `engines/live_experience_engine.py`
- `templates/live.html`
- `templates/match_detail.html`
- `static/app.css`
- `app.py`
- `tools/check_v805_api_football_live_operations_client_perfection.py`
