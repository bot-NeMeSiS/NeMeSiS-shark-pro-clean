# V553 — Picks & Recommendations Rebuild

Avance centrado en convertir partidos próximos reales en recomendaciones SHARK revisables, sin publicar picks falsos automáticamente.

## Incluye

- Nueva ruta cliente `/recomendaciones`.
- Nuevo panel admin `/admin/recommendations`.
- Nueva tabla `betting_recommendations` con migración segura.
- Motor de recomendaciones SHARK sobre partidos próximos reales.
- Score SHARK, confianza, riesgo, value label y precaución.
- APIs `/api/recommendations`, `/api/recommendations/top`, `/api/admin/intelligence-status`, `/api/admin/recommendations/generate`, `/api/admin/recommendations/convert` y `/api/betting-intelligence-check`.
- Conversión controlada de recomendación a pick en borrador o publicado.
- Integración visual con `/picks` y `/combis`.

## Seguridad y legalidad

- No inventa picks reales.
- No usa scraping ilegal.
- Si no hay odds cacheadas, marca la recomendación como análisis pendiente de cuota.
- Los picks oficiales siguen requiriendo revisión/admin.

## QA

- `app.py` compila OK con `python3 -m py_compile app.py`.
- ZIP limpio sin `.git`, sin `__pycache__`, sin DB local, sin logs y sin ZIPs antiguos.
