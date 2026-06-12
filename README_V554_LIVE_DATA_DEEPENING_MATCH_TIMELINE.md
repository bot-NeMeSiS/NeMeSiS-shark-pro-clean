# NeMeSiS SHARK PRO V554 — Live Data Deepening & Match Timeline

## Incluye
- Centro live profundo cliente: `/live-depth`
- Panel admin live depth: `/admin/live-depth`
- API resumen live: `/api/live/depth-summary`
- API reporte partido: `/api/matches/<id>/live-report`
- API timeline: `/api/live/timeline?match_id=<id>`
- Separación segura de estados: Próximo / En directo / Descanso / Finalizado
- Timeline seguro: usa eventos oficiales si existen; si no, muestra lectura contextual marcada como no oficial
- Momentum visual basado en marcador/estado/eventos disponibles
- Recomendaciones admin para mejorar fuente live

## Garantías
- No inventa eventos oficiales.
- No marca finalizados como live.
- No rompe rutas existentes.
- Mantiene V553 completo.
- `app.py` compila OK.
