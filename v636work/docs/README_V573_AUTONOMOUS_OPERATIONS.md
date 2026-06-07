# V573 — Autonomous Operations

Avance aplicado sobre V572 sin rehacer la app.

## Objetivo

Acercar NeMeSiS SHARK PRO al modelo:

> El admin supervisa. SHARK piensa. El ecosistema trabaja solo.

## Añadido

- Motor `engines/autonomous_operations_engine.py`.
- Memoria de ejecuciones automáticas en `autonomous_runs`.
- Cola de acciones operativas en `autonomous_actions`.
- Estado diario de salud en `autonomous_daily_state`.
- Registro automático de cada tarea del scheduler.
- Scoring de autonomía del ecosistema.
- Acciones pendientes para el admin: sincronizar, reparar, procesar Telegram, vigilar tareas.
- Nuevas APIs:
  - `/api/autonomous/summary`
  - `/api/autonomous/run`
- Integración visual en `/admin/data-center`.

## Qué mejora

- El admin ya no mira solo logs sueltos.
- El sistema interpreta qué tareas están vencidas, fallando o pendientes.
- Telegram, warehouse, live, odds, calendario y auto picks quedan conectados a una capa de supervisión.
- Base preparada para futuras reglas autónomas más fuertes.

## Seguridad

- No borra datos de producción.
- No cambia membresías.
- No cambia Render.
- No añade pantallas grandes nuevas.
- Usa SQLite y tablas nuevas compatibles con `/data/database.db`.
