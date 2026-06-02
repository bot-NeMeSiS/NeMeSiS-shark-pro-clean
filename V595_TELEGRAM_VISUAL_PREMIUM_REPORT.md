# V595 — Telegram Visual Premium

## Objetivo
Mejorar la presentación de picks enviados por Telegram para que sean más claros, premium y segmentados por membresía.

## Cambios aplicados
- Formato FREE / PRO / ELITE más visual y entendible.
- Mensajes con emojis, estructura clara, cuota, value, confianza, riesgo, stake, learning y SHARK V2 según plan.
- Contexto de escudos desde datos disponibles con fallback seguro a texto premium.
- Auditoría Telegram ampliada con acceso a resumen visual JSON.
- Nuevos endpoints:
  - `/api/telegram/visual-summary`
  - `/api/v595/telegram-visual-check`

## Compatibilidad
No se cambia el flujo base de Telegram: se mantiene `telegram_queue`, Auto Picks, Scheduler, filtros por membresía y envío HTTP actual.

## QA
- `compileall app.py engines database_manager.py` OK.
- ZIP limpio sin `.git`, `__pycache__`, bases de datos locales, logs ni ZIPs internos.
