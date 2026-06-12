# V560 — Data Depth & Live Expansion

Avance centrado en el siguiente cuello de botella real del proyecto: densidad de datos, profundidad live y calidad deportiva.

## Incluye
- Nueva ruta cliente `/data-depth`.
- Nuevo panel admin `/admin/data-depth`.
- API `/api/data-depth/summary`.
- API admin `/api/admin/data-depth-check`.
- API sistema `/api/system/v560-check`.
- Score global de datos, live y betting.
- Lectura de próximos partidos, resultados, escudos, odds, picks, recomendaciones y logs de sync.
- Acciones recomendadas para admin sin mostrar datos técnicos al cliente.
- Integración en menú cliente y hub admin.

## Seguridad y estabilidad
- No inventa datos deportivos.
- Usa SQLite persistente y tablas existentes si están disponibles.
- Si faltan datos, muestra estados premium claros.
- Mantiene V559 completo.
- ZIP limpio Render-ready.
