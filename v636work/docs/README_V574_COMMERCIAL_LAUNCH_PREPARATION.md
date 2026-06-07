# V574 — Commercial Launch Preparation

Avance aplicado sobre V573 sin rehacer la app.

## Qué añade

- Motor `commercial_launch_engine.py`.
- Esquema SQLite para `commercial_settings`, `commercial_launch_checks` y `commercial_daily_metrics`.
- Pricing base FREE / PRO / ELITE preparado para beta comercial.
- Checklist comercial automático: datos, cuotas, picks, Telegram, warehouse, automatización, confianza y pagos.
- Readiness score de lanzamiento.
- MRR estimado según usuarios PRO/ELITE.
- APIs admin:
  - `/api/commercial/summary`
  - `/api/commercial/rebuild`
- Integración compacta en `/admin/data-center`.

## Filosofía

No añade pantallas innecesarias. Refuerza el camino comercial:

**Datos + SHARK + Picks + Telegram + Automatización + Conversión.**

Stripe queda marcado como siguiente integración real cuando se active cobro, sin bloquear la beta comercial.
