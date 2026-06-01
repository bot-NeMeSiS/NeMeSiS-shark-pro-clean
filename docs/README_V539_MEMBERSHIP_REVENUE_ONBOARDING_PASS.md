# NeMeSiS SHARK PRO — V539 Membership Revenue + Onboarding Pass

Avance centrado en comercialización, onboarding cliente y control de membresías sin romper V538.

## Incluye
- Nueva ruta `/onboarding` para guiar al cliente.
- Nueva ruta `/mi-cuenta` como centro de cuenta del cliente.
- Nueva ruta admin `/admin/memberships`.
- API `/api/client/onboarding-check`.
- API `/api/admin/membership-summary`.
- Navegación cliente/admin mejorada.
- Estimación interna de conversión/membresías.
- Sin Stripe real todavía: preparado para monetización futura sin cobrar ni tocar pagos.

## QA
- `app.py` compila OK.
- ZIP limpio Render-ready.
- Sin `.git`, sin DB local, sin logs basura, sin `__pycache__`.
