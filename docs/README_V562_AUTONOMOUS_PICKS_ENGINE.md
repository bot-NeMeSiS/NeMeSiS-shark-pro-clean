# NeMeSiS SHARK PRO — V562 Autonomous Picks Engine

## Objetivo
Automatizar el flujo principal de valor de la app: partidos próximos + cuotas cacheadas + score SHARK = picks/recomendaciones visibles sin que el admin tenga que crearlos manualmente.

## Añadido
- Motor autónomo de picks dentro de `app.py`.
- Nueva ruta cliente `/auto-picks` y alias `/picks-automaticos`.
- Nuevo panel admin `/admin/autonomous-picks`.
- APIs:
  - `/api/autonomous-picks/status`
  - `/api/autonomous-picks/generate`
  - `/api/recommendations/auto`
- Integración con `/picks`, `/combis` y Telegram daily picks.
- Priorización de ligas importantes frente a ligas poco comerciales.
- No se inventan cuotas: si no hay cuota, se marca como análisis pendiente.

## Seguridad y legalidad
- No scraping ilegal.
- Usa partidos reales de la base SQLite.
- Usa cuotas cacheadas de Odds si existen.
- Si faltan cuotas, muestra estado claro sin fabricar datos.

## QA
- `app.py` compila OK con `python -m py_compile app.py`.
- ZIP limpio: sin `.git`, sin DB local, sin logs, sin `__pycache__`.
