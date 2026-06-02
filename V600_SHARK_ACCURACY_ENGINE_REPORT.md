# V600 — SHARK Accuracy Engine

## Objetivo
Mejorar la calidad real de los pronósticos midiendo precisión, calibración, ROI y mercados con mejor rendimiento histórico.

## Añadido
- Motor `engines/shark_accuracy_engine.py`.
- Tablas SQLite seguras: `shark_accuracy_predictions`, `shark_accuracy_calibration`, `shark_accuracy_market_rankings`, `shark_accuracy_profiles`.
- SQI: SHARK Quality Index.
- Calibración por rangos de confianza.
- Ranking de mercados por precisión, ROI y muestra.
- Endpoints `/api/shark-accuracy/summary`, `/api/shark-accuracy/rebuild` y `/api/v600/shark-accuracy-check`.
- Integración en Admin Data Center.

## Seguridad
No realiza scraping. No llama APIs externas. Solo usa datos almacenados legalmente en SQLite para generar métricas propias de NeMeSiS.

## Compatibilidad
No toca login, membresías, Telegram, Render, scheduler ni proveedores deportivos.
