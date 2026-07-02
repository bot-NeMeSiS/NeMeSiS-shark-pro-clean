# V884 Security Roles Flow QA

## Reglas preservadas

- Admin APIs protegidas sin sesion.
- Cron protegido por `AUTOMATION_SECRET`.
- No secretos expuestos.
- No DB_PATH modificado.
- No Telegram real.
- No pagos reales.
- No push/deploy automatico.

## Roles

- Cliente no debe ver rutas admin como flujo normal.
- Admin no debe recibir bottom nav o floating SHARK cliente.
- Acciones peligrosas requieren aprobacion.

## V884

El worker funcional avisa si cliente/admin se cruzan en enlaces visibles. El objetivo es evitar que una pantalla parezca funcional pero lleve a zonas incorrectas.
