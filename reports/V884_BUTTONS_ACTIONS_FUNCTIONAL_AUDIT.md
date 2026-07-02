# V884 Buttons And Actions Functional Audit

## Objetivo

Revisar que los botones y enlaces visibles no sean solo decorativos: deben tener destino real, accion clara o estado pendiente honesto.

## Cambios aplicados

- Se anadio `BAD_HREFS` al Visual Company Worker.
- Se anadio `_links_from_html()` para extraer enlaces visibles desde HTML renderizado.
- Se anadieron reglas `FUNCTIONAL_FLOW_RULES`.
- El worker ahora detecta:
  - href vacio.
  - href `#`.
  - href `javascript:void(0)`.
  - enlaces admin visibles en cliente.
  - exceso de enlaces cliente dentro de admin.
  - CTAs repetidos.

## Criterio de producto

- Cliente: cada CTA debe llevar a partidos, live, picks, SHARK, Telegram, perfil, soporte, track record o upgrade real.
- Admin: cada accion debe llevar a diagnostico, Sentinel, datos, Telegram, SHARK, pagos, membresias, usuarios o release.
- Si una accion no esta lista, se debe mostrar como `Accion pendiente`, no como boton falso.

## Pendiente

- Browser QA real para confirmar si hay botones visualmente duplicados que el HTML estatico no pueda distinguir.
