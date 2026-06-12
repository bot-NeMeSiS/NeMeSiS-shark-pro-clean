# V742 Match Detail QA Report

## Cambios

- Añadido botón para volver al calendario.
- Añadido botón para ver directo si el partido está en vivo.
- Añadido botón para picks relacionados si existen.
- Añadida sección Riesgos.
- Añadida sección Contexto.
- Mensajes prudentes cuando no hay datos suficientes.

## Reglas mantenidas

- No se inventan estadísticas.
- No se muestra UTC crudo.
- No se fuerza pick si falta cuota/mercado.
- Los escudos mantienen fallback.
- El detalle sigue usando `/match/<id>`.

## Pendiente

Validar visualmente con partidos reales de producción, especialmente nombres largos y escudos externos.
