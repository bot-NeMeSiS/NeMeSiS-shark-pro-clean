# V868 Membership Payment Value QA

Membresías:

- FREE/PRO/ELITE mantienen badges y estados visuales.
- Bloqueos y CTAs se expresan como valor, no como pantalla abandonada.
- SHARK, Telegram y picks mantienen diferencia de valor por plan cuando el dato existe.

Pagos:

- Si Stripe no está configurado, debe mostrarse `No configurado` o `Acción pendiente`.
- No se afirma `Stripe operativo`.
- No se inventan cobros, usuarios, ingresos ni pagos.
- No se tocaron pagos reales.
