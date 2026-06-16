# V804 API-Football Live Deep Tracker Pressure Field Final

## Objetivo

Seguir mejorando el directo avanzado de NeMeSiS SHARK PRO con API-Football Pro, manteniendo la experiencia visual de referencia y la regla principal: datos reales siempre, estados vacíos cuando falte información y cero simulación falsa de balón, ataques o estadísticas.

## Implementado

- Nuevo deep-sync por partido: `sync_api_football_fixture_detail()`.
- Caché independiente por fixture para no gastar API sin control al abrir detalles.
- Endpoint cliente protegido: `/api/live-tracker/match/<match_id>`.
- Campo SHARK Live enriquecido con lectura de presión calculada solo desde estadísticas reales.
- Comparativa real de estadísticas en directo:
  - posesión
  - tiros a puerta
  - tiros totales
  - tiros en área
  - córners
  - xG si API-Football lo devuelve
  - faltas
  - tarjetas
  - paradas
  - ataques / ataques peligrosos si el feed los devuelve
  - pases y precisión si el feed los devuelve
- Timeline reforzado con eventos reales de API-Football.
- Botón “Actualizar tracker” en detalle de partido con caché por partido.
- Enriquecimiento de `live_experience_engine.py` para llevar estadísticas, fase SHARK y ataques peligrosos hasta las cards de `/live`.
- Nueva UI V804:
  - ribbon de estadísticas rápidas en directo
  - comparativa local/visitante en detalle
  - chip de fase SHARK
  - aviso claro cuando ataques peligrosos o balón exacto no están disponibles.

## Protección de datos reales

La V804 no inventa:

- ubicación exacta del balón
- ataques peligrosos
- coordenadas de campo
- eventos
- estadísticas
- resultados
- cuotas
- picks

Si API-Football no devuelve un dato, la interfaz muestra pendiente/no disponible.

## Variables de entorno añadidas

```env
API_FOOTBALL_LIVE_DETAIL_CACHE_SECONDS=75
API_FOOTBALL_LIVE_DETAIL_AUTO_SYNC=true
```

## Archivos principales tocados

- `VERSION.txt`
- `app.py`
- `engines/api_football_live_tracker_engine.py`
- `engines/live_experience_engine.py`
- `templates/live.html`
- `templates/match_detail.html`
- `static/app.css`
- `.env.example`
- `.env.render.clean`
- `tools/check_v804_api_football_deep_live_tracker.py`

## No tocado

- DB_PATH
- secretos reales
- Render Cron
- Telegram real
- usuarios
- sesiones
- membresías
- pagos
- lógica core de picks
- Madrid Time
