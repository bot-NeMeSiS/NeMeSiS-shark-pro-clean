# V782 Stripe real subscriptions / membership billing

## Objetivo
Activar pagos reales controlados para PRO y ELITE usando Stripe Checkout y webhooks verificados, sin tocar DB_PATH, Telegram, Cron, picks, Track Record, highlights ni Data Marketplace.

## Implementado
- Nuevo motor `engines/stripe_payments_engine.py`.
- Checkout de suscripción para PRO y ELITE.
- Portal de cliente Stripe opcional.
- Webhook real `/api/payments/stripe-webhook` con verificación de firma `STRIPE_WEBHOOK_SECRET`.
- Aplicación automática de membresía al recibir eventos verificados.
- Downgrade a FREE al recibir cancelación/unpaid/expired cuando la membresía viene de Stripe.
- Tablas `stripe_checkout_sessions` y `stripe_subscriptions`.
- Columnas Stripe en `users` para cliente, suscripción, estado y periodo.
- Pantalla `/membresias` preparada para pagar con Stripe.
- Pantalla `/mi-cuenta` con estado de suscripción y acceso al portal.
- Panel `/admin/payments` convertido en centro de control Stripe.
- Nuevo check `tools/check_v782_stripe_real_subscriptions.py`.

## Eventos manejados
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.paid`
- `invoice.payment_failed`
- `invoice.payment_action_required`

## Seguridad
- No se guardan claves Stripe en el ZIP.
- Los webhooks reales no aplican membresía si no pasan firma Stripe.
- Checkout requiere usuario logueado.
- Los formularios usan CSRF salvo webhook, que está exento por ser endpoint externo firmado.
- El portal solo abre si existe `stripe_customer_id` asociado al usuario.

## Variables Render necesarias
- `PAYMENTS_ENABLED=true`
- `PAYMENTS_MODE=stripe_real`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_PRO`
- `STRIPE_PRICE_ELITE`
- `STRIPE_CUSTOMER_PORTAL_ENABLED=true`
- `APP_PUBLIC_URL=https://bot-apuestas-crgf.onrender.com`

## Prueba recomendada en Stripe test mode
1. Configurar productos/precios recurrentes PRO y ELITE en Stripe.
2. Copiar los Price IDs a Render.
3. Crear webhook en Stripe hacia `/api/payments/stripe-webhook`.
4. Copiar el signing secret a `STRIPE_WEBHOOK_SECRET`.
5. Entrar con usuario cliente y pagar PRO en `/membresias`.
6. Confirmar que vuelve a `/mi-cuenta`.
7. Confirmar que el webhook cambia la membresía a PRO.
8. Cancelar en Stripe/portal y confirmar retorno a FREE cuando llegue el evento correspondiente.
