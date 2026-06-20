# V829 Mobile Real Video And Reference Gap Audit

## Lectura inicial

V828 mejoró mucho el sistema visual desktop, pero el móvil todavía necesitaba un cierre más contundente:

- topbar compacta pero con demasiadas capas heredadas;
- rail desktop debía desaparecer siempre en móvil;
- falta de accesos secundarios rápidos a perfil, Telegram, favoritos, histórico y soporte;
- cards todavía grandes en algunas rutas;
- filtros y acciones necesitaban scroll horizontal suave;
- SHARK flotante debía quedar alto sobre bottom nav y oculto en sus propias pantallas;
- admin necesitaba protección contra tablas desbordadas.

## Pantallas cliente revisadas

- `/`: landing premium, ahora bajo capa móvil V829.
- `/cliente-login`: topbar y formulario con tamaño móvil seguro.
- `/registro`: mismo sistema visual que login.
- `/app`: dashboard principal, cards y hero compactados por CSS móvil.
- `/partidos` y `/calendar`: filtros horizontales, rows a una columna en 390/430px.
- `/live` y `/directo`: live cards y scoreboard a una columna, sin inventar datos.
- `/picks`: pick destacado y cards secundarias en columna.
- `/match/<id>`: detalle protegido por shell móvil y botones conectados.
- `/shark`, `/shark-ai`, `/shark-core`: sin floating duplicado.
- `/profile`, `/telegram`, `/support`: accesos secundarios V829 visibles desde móvil.
- `/favorites`, `/track-record`, `/combis`, `/mercados`, `/highlights`: cards compactas, bottom nav y quick links.

## Pantallas admin revisadas

Admin queda sin bottom nav cliente y sin floating SHARK. En móvil, tablas y paneles tienen overflow horizontal seguro.

## Qué se corrige

- Safe-area móvil.
- Bottom nav única.
- Floating SHARK único.
- Sidebar desktop oculto en móvil.
- Quick links secundarios enlazados.
- Cards y heroes compactados.
- Botones mínimo 44px.
- Filtros con scroll horizontal.
- Admin responsive con tablas desplazables.
