# V926 Desktop Reference Model Audit

## Evidencia anterior

La auditoria V925 previa al cambio, realizada a 1440 x 900, encontro:

- Home: hero de aproximadamente 500 px y solo cuatro cards visibles antes del primer scroll.
- Calendar: contenido util situado tras varias capas historicas; altura renderizada aproximada de 4488 px.
- Live: filtros y board real por debajo de capas de diagnostico; altura aproximada de 2981 px.
- Picks: informacion repetida antes del contenido principal; altura aproximada de 2149 px.
- Admin: heroes y strips historicos duplicaban contexto y reducian densidad operativa.

## Cambios estructurales

- La capa V926 se activa solo con `@media (min-width: 1024px)`.
- Ancho de trabajo ampliado hasta 1600 px para pantallas grandes.
- Hero home fijado a 388 px en desktop y resumen de hoy en columna lateral.
- Capas historicas redundantes se ocultan solo en desktop; movil conserva el flujo anterior.
- Calendar/live/picks usan orden visual explicito: hero, estado seguro, filtros, datos.
- Grids admin pasan a 3/4 columnas cuando el ancho lo permite.

## Limite de QA

El navegador de esta sesion rechazo el servidor local por politica del entorno. No se genero captura V926 y no se declara paridad visual. La validacion realizada es de HTML renderizado, CSS, rutas, Jinja y Sentinel.

