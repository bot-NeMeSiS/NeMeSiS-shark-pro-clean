# V803 API-Football Live Tracker Reference Experience

## Objetivo
Convertir `/live` y el detalle de partido en una experiencia tipo app premium usando API-Football Pro cuando la clave de pago está configurada, manteniendo la regla de datos reales: no se inventan coordenadas de balón, ataques peligrosos ni estadísticas.

## Cambios
- Nuevo motor `engines/api_football_live_tracker_engine.py`.
- Sincronización controlada de `/fixtures?live=all`, `/fixtures/events` y `/fixtures/statistics` con caché.
- Caché SQLite nueva: `api_football_live_snapshots`, `api_football_live_events`, `api_football_live_stats`, `api_football_live_sync_state`.
- `/live` prioriza API-Football Pro y luego conserva las fuentes existentes.
- `/api/live` incluye estado del live tracker.
- Nuevos endpoints cliente protegidos: `/api/live-tracker` y `/api/live-tracker/status`.
- Detalle `/match/<id>` muestra campo SHARK Live, presión calculada desde estadísticas reales, eventos y disponibilidad de balón exacto.
- CSS V803 para campo visual, timeline y estado de proveedor.

## Protección de créditos/API
- `API_FOOTBALL_LIVE_CACHE_SECONDS=55` por defecto.
- `API_FOOTBALL_LIVE_DEEP_LIMIT=8` por defecto para limitar eventos/estadísticas profundas.
- `refresh=1` fuerza actualización manual.

## Regla de datos reales
- Si no hay estadísticas, se muestra pendiente.
- Si no hay eventos, se muestra pendiente.
- Si API-Football no ofrece coordenadas exactas de balón, la app muestra “Balón exacto no disponible: no se inventa”.
- La presión SHARK se calcula solo con estadísticas reales disponibles: posesión, tiros, córners y tarjetas.

## No tocado
- DB_PATH
- AUTOMATION_SECRET
- Telegram/Cron
- usuarios/sesiones/membresías
- pagos
- picks core
- Madrid Time
