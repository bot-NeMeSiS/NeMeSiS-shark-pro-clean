# V578 — Telegram Autonomous Delivery

Avance centrado en automatización Telegram sin añadir pantallas grandes.

## Añadido

- Motor `telegram_autonomous_delivery_engine.py`.
- Campañas automáticas para resumen diario, picks PRO y alertas ELITE.
- Reglas por membresía FREE / PRO / ELITE.
- Memoria anti-duplicados por día, pick, usuario y chat.
- Cola segura en `telegram_queue`, sin enviar directamente hasta procesar cola.
- APIs:
  - `/api/telegram-autonomous/summary`
  - `/api/telegram-autonomous/run`
  - `/api/system/v578-check`
- Integración en Data Center mediante acción `telegram_autonomous`.

## Filosofía

El admin supervisa. SHARK decide qué merece salir. Telegram reparte con control, membresía y anti-spam.
