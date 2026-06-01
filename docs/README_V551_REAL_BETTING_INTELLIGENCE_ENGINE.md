# V551 — Real Betting Intelligence Engine

Avance centrado en recomendaciones automáticas serias para apuestas.

Incluye:
- motor de inteligencia de apuestas sobre datos persistidos
- scoring SHARK por partido
- lectura de valor de cuota si hay odds cacheadas
- riesgo BAJO/MEDIO/ALTO
- confianza y score
- rutas `/api/recommendations` y `/api/recommendations/top`
- panel admin `/admin/intelligence-engine`
- estado `/api/admin/intelligence-status`
- conversión controlada de recomendación a pick desde admin

Importante: no inventa picks reales. Si no hay cuotas/datos suficientes, marca watchlist o seguimiento.
