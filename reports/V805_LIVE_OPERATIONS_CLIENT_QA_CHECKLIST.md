# V805 Live Operations Client QA Checklist

## Render

- Confirmar `API_FOOTBALL_KEY` configurada.
- Confirmar `ENABLE_API_FOOTBALL_PROVIDER=true`.
- Confirmar `ENABLE_API_FOOTBALL_LIVE_TRACKER=true`.
- Abrir `/live?refresh=1` con sesión cliente.
- Abrir `/api/live-tracker/quality` con sesión cliente.
- Revisar que no aparecen datos inventados cuando no haya live avanzado.

## Cliente

- `/live` debe mostrar estado de API-Football, caché, calidad y evidencias.
- Cada card debe enlazar a `/match/<id>`.
- El partido live debe tener enlace a `#live-tracker` y SHARK.
- Si no hay ataques peligrosos, debe decir no disponible.
- Si no hay posición de balón, debe decir que no se simula.

## Detalle de partido

- Botón `Actualizar tracker` funciona sin romper el partido.
- Comparativa de estadísticas aparece solo cuando API-Football la trae.
- Timeline aparece solo con eventos reales.
- Presión SHARK se calcula con estadísticas reales.
