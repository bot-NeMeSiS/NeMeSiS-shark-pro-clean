# V589 — Calendario Pro Match Center

## Objetivo

Convertir el calendario en una vista real de app deportiva premium para consultar partidos próximos, pasados y en directo, sin crear menús innecesarios ni romper Live, Telegram, SHARK, membresías o Render.

## Cambios principales

- Nueva capa `calendar_pro_center()` para construir calendario desde SQLite.
- Nueva función `calendar_query_matches()` con modos:
  - Hoy
  - Semana
  - Próximos
  - Pasados
  - En directo
  - Top mundial
  - España
  - Andalucía
- Nueva navegación por días alrededor de la fecha elegida.
- Agrupación por día, competición y hora.
- Soporte de escudos local/visitante con fallback seguro.
- Estados visibles: Próximo, En directo, Descanso, Finalizado.
- Resultados pasados con marcador cuando existe.
- Enlace directo de cada partido a `/partido/<id>`.
- Nuevo endpoint `/api/v589/calendar-check`.
- `/api/calendar` devuelve ahora estructura de calendario pro.
- CSS específico para calendario premium y responsive móvil.

## Archivos modificados

- `app.py`
- `templates/calendar.html`
- `static/app.css`
- `VERSION.txt`

## QA

- `compileall app.py engines database_manager.py` OK.
- No se toca login.
- No se toca Telegram.
- No se toca Auto Picks.
- No se toca SHARK Learning.
- No se toca Render.
- No se inventan partidos: el calendario usa la tabla `matches` existente.

## Rutas importantes

- `/calendario`
- `/calendario?mode=future`
- `/calendario?mode=past`
- `/calendario?mode=week`
- `/calendario?mode=live`
- `/api/calendar`
- `/api/v589/calendar-check`
