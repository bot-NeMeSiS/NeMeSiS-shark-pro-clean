# V881 Screen By Screen Nav QA

## Cliente

Rutas revisadas por smoke local: `/`, `/app`, `/partidos`, `/calendar`, `/live`, `/picks`, `/shark`, `/telegram`, `/profile`, `/track-record`.

Resultado esperado por markup:

- una nav desktop cliente;
- una bottom nav móvil cliente;
- sin rail lateral cliente duplicado;
- floating SHARK oculto en rutas SHARK.

## Admin

Rutas revisadas por smoke local: `/admin/dashboard`, `/admin/company-os`, `/admin/company-audit`, `/admin/continuous-sentinel`, `/admin/sentinel-workflow`, `/admin/data-center`, `/admin/telegram/command-center`, `/admin/users`, `/admin/memberships`, `/admin/payments`.

Resultado esperado por markup:

- una nav admin: `v808-admin-rail`;
- sin bottom nav cliente;
- sin floating SHARK cliente;
- sin dock/command strip duplicados.
