# V832 Mobile Final No Fail QA

## Objetivo

Mantener la corrección V830 de bottom nav y extender coherencia móvil a toda la app.

## Confirmado por diseño

- Bottom nav centrada y con cinco enlaces.
- Floating SHARK por encima de la navegación.
- `/shark`, `/shark-ai`, `/shark-core` sin floating duplicado.
- Admin sin bottom nav cliente ni SHARK cliente.
- Safe-area inferior aplicada.
- Contenedores con `max-width:100%` y `min-width:0`.
- Botones con altura táctil adecuada.
- Cards más compactas en mobile.

## Rutas revisadas

`/`, `/cliente-login`, `/registro`, `/app`, `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/match/<id>`, `/shark`, `/profile`, `/telegram`, `/support`, `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`.
