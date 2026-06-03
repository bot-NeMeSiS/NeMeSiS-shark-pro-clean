# V587 — Performance Proof & ROI Dashboard

## Objetivo

Mostrar rendimiento histórico real de SHARK para aumentar transparencia, confianza y conversión.

## Implementado

- Nuevo motor: `engines/shark_performance_engine.py`.
- Tablas SQLite seguras:
  - `shark_performance_daily`
  - `shark_performance_summary`
- Métricas calculadas:
  - ROI histórico
  - Winrate histórico
  - Beneficio acumulado en unidades
  - Stake acumulado
  - Picks ganados/perdidos/nulos/pendientes
  - Racha actual
  - Mejor racha positiva
  - Peor racha negativa
  - Estadísticas por liga
  - Estadísticas por mercado
  - Historial reciente de picks
- Lectura tolerante desde:
  - `warehouse_pick_facts`
  - `historical_picks`
  - `picks`
- Endpoints:
  - `/api/performance/summary`
  - `/api/performance/rebuild`
- Integración:
  - Dashboard cliente
  - Dashboard admin
  - API de SHARK Learning
  - Admin Data Center mediante acción `shark_performance`

## Protección y compatibilidad

- No se toca Telegram.
- No se toca Auto Picks.
- No se toca Live.
- No se cambia membresías.
- No se cambia Render.
- No se pide borrar DB.
- Migraciones seguras con `CREATE TABLE IF NOT EXISTS` y `ALTER TABLE` defensivo.

## Pruebas

- `compileall app.py engines`: OK.
- Prueba SQLite temporal:
  - Crea `historical_picks`.
  - Reconstruye `shark_performance_daily`.
  - Reconstruye `shark_performance_summary`.
  - Calcula ROI 30.0%, winrate 66.67% y racha actual positiva.

## Resultado

El cliente puede ver rendimiento real de SHARK desde su dashboard y el admin puede auditar ROI, winrate, beneficio, rachas, ligas, mercados e historial reciente.

