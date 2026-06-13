# V766 Client Calendar Highlights QA

## Pantallas revisadas
- `/calendar`
- `/calendar?lane=results`
- `/live`
- `/live?f=finished`
- `/highlights`
- `/match/<id>`
- `/`

## Criterios de calidad
- El cliente ve directos, resultados y próximos separados.
- El calendario ya no ofrece Andalucía como filtro principal vacío.
- Los partidos finalizados muestran resultado si existe.
- Los resúmenes aparecen como enlaces externos si la API los aporta.
- Si no hay resumen, se muestra “Resumen pendiente” sin romper la pantalla.
- Todo sigue en hora Madrid.
- No hay textos admin ni JSON técnico en vistas cliente.

## Pendiente de producción
La disponibilidad real de highlights depende de la API y de que la clave esté configurada en Render.
