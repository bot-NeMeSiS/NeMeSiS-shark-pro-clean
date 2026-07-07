# V782 Stripe Render runbook

## Configuración mínima en Render

```txt
PAYMENTS_ENABLED=true
PAYMENTS_MODE=stripe_real
APP_PUBLIC_URL=https://bot-apuestas-crgf.onrender.com
STRIPE_SECRET_KEY=***hidden***
STRIPE_WEBHOOK_SECRET=***hidden***
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ELITE=price_...
STRIPE_CUSTOMER_PORTAL_ENABLED=true
```

## Endpoint webhook

```txt
https://bot-apuestas-crgf.onrender.com/api/payments/stripe-webhook
```

Eventos recomendados:

```txt
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.payment_succeeded
invoice.payment_failed
invoice.payment_action_required
```

## Rutas de prueba

```txt
/membresias
/mi-cuenta
/admin/payments
/api/admin/payments
```

## Nota
Stripe Checkout y el portal usan la librería oficial `stripe` instalada desde `requirements.txt`. Si Render no reinstala dependencias tras subir ZIP, fuerza redeploy limpio.
