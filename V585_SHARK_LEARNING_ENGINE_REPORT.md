# V585 — SHARK Learning Engine

## Objetivo

Activar una capa de aprendizaje histórico para que SHARK ajuste automáticamente la confianza de picks y recomendaciones según rendimiento real.

## Implementado

- Nuevo motor central: `engines/shark_learning_engine.py`.
- Tablas SQLite seguras:
  - `shark_learning_profiles`
  - `shark_learning_market_stats`
  - `shark_learning_league_stats`
  - `shark_learning_odds_ranges`
- Funciones principales:
  - `build_shark_learning_profile()`
  - `rebuild_shark_learning_engine()`
  - `apply_shark_learning_adjustment()`
- Lectura de histórico desde:
  - `warehouse_pick_facts`
  - `historical_picks`
  - `picks` como fallback
- Ajustes automáticos por mercado, liga y rango de cuota.
- Explicaciones visibles:
  - Histórico insuficiente: confianza sin ajuste avanzado.
  - SHARK aumenta la confianza por buen rendimiento histórico en este mercado.
  - SHARK reduce la confianza por baja fiabilidad reciente en esta liga.
  - Patrón favorable detectado.
  - Patrón desfavorable detectado.
- Endpoints admin:
  - `/api/shark-learning/summary`
  - `/api/shark-learning/rebuild`
- Integración en:
  - Auto Picks
  - Picks publicados
  - Recomendaciones
  - Admin Data Center
- Logs:
  - `[SHARK_LEARNING]`
  - `[SHARK_MEMORY]`
  - `[PICKS]`
  - `[WAREHOUSE]`

## Pruebas

- `compileall app.py engines`: OK.
- Prueba temporal SQLite:
  - Crea `historical_picks`.
  - Reconstruye perfil.
  - Aplica ajuste histórico.
  - Resultado: lectura de 6 picks y ajuste positivo aplicado.

## Riesgos

- El aprendizaje avanzado depende de muestra real suficiente. Con pocos picks resueltos, SHARK mantiene confianza sin ajuste agresivo.
- La fiabilidad subirá de calidad conforme el warehouse tenga más picks ganados/perdidos con cuota y stake.

