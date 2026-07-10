# V927 Client PC Dashboard QA

`/app`, `/profile`, `/shark`, `/telegram` y `/membresias` reciben el sistema V927 sin alterar el comportamiento movil.

- Dashboard PC con seis KPIs y panel lateral de siguiente accion.
- Hora Madrid, plan y disponibilidad de datos visibles.
- SHARK distingue proveedor IA, capacidades, limites y datos usados.
- Telegram conserva vinculacion, no filler, dedupe y ausencia de envio real.
- Perfil y membresias usan grids amplios y checkout solo si Stripe esta configurado.
- Sin sesion, las rutas privadas redirigen de forma controlada; no hay 500.
