# V785 Membership Stripe Flow Price Polish

## Objetivo

Corregir el flujo comercial de planes después de activar Stripe real: el cliente debe ver precios claros, elegir PRO/ELITE desde inicio o membresías, iniciar sesión si hace falta y volver al plan elegido para pagar sin perderse.

## Cambios

- Se añade `/comprar/<plan>` y `/planes/<plan>` para recordar PRO/ELITE antes de login/registro.
- `cliente-login` y `registro` conservan `next` seguro y `plan`.
- `/membresias` muestra plan seleccionado y CTA `Continuar a Stripe`.
- Home pública enlaza PRO/ELITE a la ruta de compra, no solo a una página genérica.
- Precio visible PRO: `9,99 €/mes`.
- Precio visible ELITE: `24,99 €/mes`.
- El motor Stripe mantiene los IDs `price_...` para Checkout, pero separa el texto comercial visible con `STRIPE_PRICE_*_LABEL`.

## Prueba recomendada

1. Abrir `/` sin sesión.
2. Pulsar PRO.
3. Confirmar que va a login con `PRO seleccionado`.
4. Entrar o registrar cuenta.
5. Confirmar vuelta a `/membresias?plan=PRO&continuar_pago=1`.
6. Pulsar `Continuar a Stripe`.
7. Completar tarjeta de prueba en Stripe.
8. Verificar que webhook activa PRO/ELITE.

## No tocado

Telegram, Cron, DB_PATH, usuarios existentes, picks, resultados, live, escudos, Track Record, Data Marketplace, Automation Center y webhook Stripe se conservan.
