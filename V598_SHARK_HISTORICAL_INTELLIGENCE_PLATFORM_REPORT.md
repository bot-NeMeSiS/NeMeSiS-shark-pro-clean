# V598 — SHARK Historical Intelligence Platform

## Objetivo

Convertir los datos deportivos recibidos de fuentes autorizadas en un activo historico propio de NeMeSiS SHARK PRO.

## Añadido

- Motor `engines/shark_historical_intelligence_engine.py`.
- Registro legal/operativo de fuentes: API-Football, TheSportsDB, The Odds API y NeMeSiS SHARK.
- Hechos historicos normalizados de partidos.
- Forma y rating historico por equipo.
- Perfiles historicos por liga.
- Perfiles derivados por mercado.
- Métricas de calidad y profundidad de datos.
- Integración en scheduler `warehouse`.
- Integración en Admin Data Center.
- APIs `/api/historical-intelligence/summary`, `/api/historical-intelligence/rebuild` y `/api/v598/historical-intelligence-check`.

## Nota legal

La plataforma conserva datos para uso interno, operación, aprendizaje SHARK y métricas derivadas propias. No redistribuye datos crudos de terceros ni crea una API pública de datos copiados.

## Resultado

Cada sincronización del warehouse deja más memoria histórica y crea un activo acumulativo para mejorar picks, predicciones, ratings y futuras decisiones comerciales.
