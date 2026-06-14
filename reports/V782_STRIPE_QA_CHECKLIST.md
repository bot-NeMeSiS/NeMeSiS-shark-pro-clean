# V782 Stripe QA checklist

- [ ] `/admin/payments` muestra `Stripe Checkout OK`.
- [ ] `/admin/payments` muestra `Webhook verificado OK`.
- [ ] `/membresias` muestra botones PRO y ELITE habilitados.
- [ ] PRO abre Stripe Checkout.
- [ ] ELITE abre Stripe Checkout.
- [ ] `checkout.session.completed` queda registrado.
- [ ] Usuario cambia a PRO/ELITE tras webhook verificado.
- [ ] `/mi-cuenta` muestra estado Stripe y renovación.
- [ ] Portal Stripe abre si el usuario tiene customer asociado.
- [ ] Cancelación o deleted devuelve a FREE si la membresía venía de Stripe.
- [ ] No se expone secret ni whsec en HTML/admin.
