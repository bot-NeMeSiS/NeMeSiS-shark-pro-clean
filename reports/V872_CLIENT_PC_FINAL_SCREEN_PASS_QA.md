# V872 cliente PC final pass

## Revisión

Pantallas objetivo: `/app`, `/partidos`, `/live`, `/picks`, `/shark`, `/telegram`, `/track-record`.

## Correcciones V872

- Las filas de acciones y CTAs se mantienen dentro de su contenedor.
- Los empty states reducen altura mínima cuando no hay datos reales.
- Se limita el ancho de textos de estados vacíos para evitar bloques visuales pobres.
- Se preservan estados seguros: `Sin datos reales`, `Esperando proveedor`, `Sin picks activos`, `Cuota pendiente`, `Selección pendiente`, `Pick en revisión`.

## No realizado

- No se rediseñan pantallas ni se añaden features.
- No se inventan partidos, picks, cuotas ni resultados.
- No se certifica Render V872 hasta deploy.
