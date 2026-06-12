# V575 — Revenue & Subscription Control

Avance enfocado en preparación comercial real sin activar cobros todavía.

## Añadido

- Motor `subscription_control_engine.py`.
- Tablas SQLite:
  - `subscription_accounts`
  - `subscription_events`
  - `revenue_daily_metrics`
- Sincronización segura desde usuarios existentes.
- Control de estado por usuario: `active`, `trialing`, `grace`, `past_due`.
- Gracia automática de 3 días para PRO/ELITE caducados.
- Bloqueo suave cuando vence la gracia.
- MRR estimado y conversión pagada.
- Acciones comerciales para el admin.
- Integración en `/admin/data-center`.
- APIs:
  - `/api/subscriptions/summary`
  - `/api/subscriptions/apply-rules`

## Importante

No cobra dinero ni exige Stripe todavía. Deja la base preparada para conectar Stripe más adelante sin romper membresías actuales.
