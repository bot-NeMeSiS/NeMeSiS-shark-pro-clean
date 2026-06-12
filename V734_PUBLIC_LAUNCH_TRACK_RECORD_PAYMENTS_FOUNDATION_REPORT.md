# V734_PUBLIC_LAUNCH_TRACK_RECORD_PAYMENTS_FOUNDATION

## Objetivo

V734 avanza los 6 pasos necesarios para acercar NeMeSiS SHARK PRO al público grande sin romper lo que ya funciona. No rehace la app, no toca secrets reales, no cambia `DB_PATH=/data/database.db`, no rompe Telegram/Cron/Madrid Time/V733 y no activa cobros automáticos.

## Añadido

### 1. Centro de lanzamiento comercial

- Nueva ruta admin: `/admin/public-launch`
- Alias admin: `/admin/commercial-launch`
- Nueva API segura: `/api/admin/public-launch`
- Nuevo motor: `engines/public_launch_engine.py`

El centro evalúa 6 áreas:

1. Producción Render certificada.
2. Telegram producción estable.
3. Persistencia y Data Memory.
4. Track record, resultados y ROI.
5. Pagos PRO/ELITE.
6. Arquitectura y tests.

### 2. Track Record y ROI real

- Nueva ruta pública/cliente: `/track-record`
- Alias: `/rendimiento-picks`
- Nueva ruta admin: `/admin/track-record`
- Nueva API pública: `/api/track-record`
- Nueva API admin: `/api/admin/track-record`
- Integra `engines/pick_grading_engine.py` existente.

Permite analizar picks con resultados reales y deja pendiente cualquier mercado que no pueda validarse con seguridad. No inventa aciertos.

### 3. Pagos PRO/ELITE foundation

- Nueva ruta admin: `/admin/payments`
- Nueva API admin: `/api/admin/payments`
- Nuevo webhook seguro/auditoría: `/api/payments/stripe-webhook`
- Nuevo motor: `engines/payment_readiness_engine.py`

V734 no cobra a nadie ni cambia membresías automáticamente. Prepara variables, auditoría de webhooks, suscripciones internas y bloqueos antes de activar pagos reales.

### 4. Suscripciones y downgrade foundation

Integra `engines/subscription_control_engine.py` para revisar:

- FREE / PRO / ELITE.
- MRR estimado.
- usuarios pagados activos.
- gracia / past_due / soft block.
- riesgos antes de monetización real.

### 5. Navegación y experiencia

- Añadido acceso admin a `Lanzamiento`.
- Añadido acceso cliente a `Histórico`.
- Añadido acceso desde menú cliente a track record.
- Añadidos accesos admin a Público grande, Track Record y Pagos.
- Pulido CSS V734 para centros de lanzamiento, pagos y rendimiento.

### 6. QA técnica

- Nuevo script: `tools/check_v734_public_launch.py`
- Actualizado `tools/check_v729_security.py` para aceptar versiones superiores a V733.
- Arreglado `templates/pick_tracking.html` para usar CSRF en fetch y corregir símbolos/textos.

## Validación local ejecutada

- `python -m py_compile app.py engines/payment_readiness_engine.py engines/public_launch_engine.py tools/check_v734_public_launch.py`: OK
- `python -m compileall -q .`: OK
- `python tools/check_madrid_times.py`: OK
- `python tools/check_v728_client_experience.py`: OK
- `python tools/check_v729_security.py`: OK
- `python tools/check_v730_route_health.py`: OK
- `python tools/check_v731_client_experience.py`: OK
- `python tools/check_v732_production_readiness.py`: OK
- `python tools/check_v733_client_success.py`: OK
- `python tools/check_v734_public_launch.py`: OK
- Parseo Jinja templates: OK

## Limitaciones honestas

Este sandbox no tiene Flask instalado, así que aquí no se pudo ejecutar `smoke_check.py`, `validate_release.py` ni `pytest -q`. Tampoco se pudo validar producción real de Render, Telegram real ni Stripe real desde aquí.

## Pendiente en Render

Después de desplegar V734:

1. Revisar `/api/runtime-version`.
2. Entrar a `/admin/public-launch`.
3. Entrar a `/admin/production-readiness`.
4. Entrar a `/admin/telegram/command-center`.
5. Entrar a `/admin/track-record`.
6. Entrar a `/admin/payments`.
7. Confirmar Cron 403/200.
8. Confirmar Telegram real.
9. Confirmar `DB_PATH=/data/database.db`.
10. Configurar variables Stripe solo cuando se vaya a probar pagos reales.

## Seguridad

- No se incluyen secrets reales.
- No se exponen tokens ni claves.
- Webhook de pagos queda en modo auditoría.
- No se aplican cambios automáticos de membresía por pagos en V734.
- Cron/webhooks siguen protegidos por sus mecanismos existentes.
