# V592 — SHARK Prediction Evolution

## Objetivo

Mejorar la calidad de los pronósticos sin añadir nuevas pantallas ni romper el flujo actual. Esta versión convierte SHARK en un motor más explicable: ratings internos, fuerza de competición, selección de mercado y desglose de confianza.

## Añadido

- Motor `engines/shark_prediction_engine.py`.
- Tablas SQLite seguras:
  - `shark_team_ratings`
  - `shark_league_strength`
  - `shark_prediction_market_scores`
  - `shark_prediction_profiles`
- Rating interno de equipos desde resultados guardados.
- Fuerza de ligas/competiciones desde histórico.
- Selección de mercado recomendada.
- Score SHARK V2.
- Desglose de confianza por factores.
- Advertencias cuando la muestra histórica es baja.
- Integración en ficha de partido.
- Integración en Auto Picks con ajuste conservador.
- Integración en Admin Data Center.
- Endpoints:
  - `/api/shark-prediction/summary`
  - `/api/shark-prediction/rebuild`
  - `/api/v592/shark-prediction-check`

## Filosofía

No inventa datos externos. Usa únicamente SQLite, resultados guardados, learning existente, cuotas/value y contexto premium del partido.

## Seguridad

No se toca login, membresías, Telegram, Render ni la base de datos existente. Solo se crean tablas propias si no existen.

## Validación

- `compileall app.py engines` OK.
- ZIP limpio sin `.git`, `__pycache__`, bases de datos locales, logs ni ZIPs internos.
