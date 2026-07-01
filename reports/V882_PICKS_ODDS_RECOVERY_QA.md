# V882 Picks Odds Recovery QA

## Revisión

- `/picks`: 200 local con DB temporal.
- `/api/picks`: 200 local con DB temporal.
- Picks publicados visibles en DB temporal: 0.
- No se muestra cuota falsa.
- No se muestra selección inventada.

## Fix seguro

El empty state de picks ahora diferencia:

- Sin picks activos.
- Cuota pendiente.
- Selección pendiente.
- Pick en revisión.
- Sin pick real publicado.

No se creó ningún pick nuevo.
