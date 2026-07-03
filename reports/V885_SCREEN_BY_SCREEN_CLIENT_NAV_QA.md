# V885 Screen By Screen Client Navigation QA

## Cliente

Rutas previstas para smoke local:

- /
- /app
- /partidos
- /calendar
- /live
- /directo
- /picks
- /shark
- /telegram
- /profile
- /track-record
- /support

Estado esperado:

- Visitante/publico: topbar publica simple.
- Cliente autenticado desktop: `ns-client-sidebar`.
- Cliente movil: bottom nav.
- Sin enlaces `#`.
- Sin `javascript:void(0)`.
- Sin admin nav en cliente.

## Admin

Rutas previstas:

- /admin/dashboard
- /admin/continuous-sentinel
- /admin/visual-worker
- /admin/data-center
- /admin/telegram/command-center
- /admin/payments

Estado esperado:

- Sin sidebar cliente.
- Sin bottom nav cliente.
- Sin floating SHARK cliente.
- Proteccion por sesion cuando proceda.
