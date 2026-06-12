# V576 — SHARK Performance Memory

Avance enfocado en mejorar SHARK sin añadir pantallas innecesarias.

## Incluye

- Nuevo motor `engines/shark_performance_memory_engine.py`.
- Tablas `shark_performance_memory` y `shark_pick_learning_runs`.
- Lectura de picks históricos desde `warehouse_pick_facts` y fallback a `picks`.
- Patrones por mercado, liga, selección, rango de confianza, mercado+confianza y liga+mercado.
- ROI, winrate, muestra, beneficio, fiabilidad y ajuste SHARK.
- Integración en `/admin/data-center`.
- APIs:
  - `/api/shark-memory/summary`
  - `/api/shark-memory/rebuild`

## Objetivo

Que SHARK empiece a recordar qué tipos de picks funcionan y cuáles generan riesgo, preparando la plataforma para automatización y Machine Learning futuro.

No activa cobros, no borra datos y no rompe el flujo existente.
