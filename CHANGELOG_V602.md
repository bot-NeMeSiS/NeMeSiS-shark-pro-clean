# CHANGELOG V602 — SHARK Visibility Layer

## Objetivo

Hacer visible la inteligencia que SHARK ya calcula sin rehacer la app, sin cambiar Render, sin tocar membresías y sin modificar el diseño general.

## Partido

- La vista de detalle de partido muestra:
  - SHARK Score
  - Confianza contextual
  - Riesgo
  - Momentum local
  - Momentum visitante
  - Presión
  - Dominancia
  - Alertas SHARK cuando existan

## Live

- Las tarjetas live muestran:
  - Momentum Local
  - Momentum Visitante
  - Riesgo
  - Alertas SHARK principales

## Picks

- Cada pick publicado ahora explica:
  - Por qué entrar
  - Riesgos detectados
  - Stake sugerido
  - Confianza SHARK
  - Value detectado

## Recomendaciones

- Cada recomendación muestra de forma explícita:
  - Score SHARK
  - Motivo principal
  - Riesgo
  - Nivel de confianza

## Admin

- `/admin/final-qa` incluye verificación del warehouse:
  - `historical_matches`
  - `historical_picks`
  - `historical_recommendations`

## Compatibilidad

- Login, registro, admin, Telegram, SQLite, Render, SHARK y membresías se mantienen sin cambios estructurales.
