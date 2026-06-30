# V860 Legacy Routes Buttons And Duplicates Audit

## Duplicidades detectadas

- Admin: top nav + rail + dock + command strip.
- Cliente: top nav + quick actions + rail lateral + bottom nav + floating SHARK.

## Acción V860

- No se eliminaron rutas.
- Se redujo la duplicidad visible con CSS V860:
  - admin top nav oculto;
  - admin dock oculto;
  - bottom nav y floating SHARK del cliente siguen ocultos en admin;
  - cliente prioriza rail desktop y top actions solo en rangos móviles más estrechos.

## Estado

- Las rutas principales siguen presentes.
- No se detectó necesidad de borrar endpoints legacy en esta pasada.
- La limpieza principal es visual y de release, no de routing destructivo.
