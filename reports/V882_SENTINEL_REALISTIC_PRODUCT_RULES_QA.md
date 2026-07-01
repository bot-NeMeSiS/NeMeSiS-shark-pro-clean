# V882 Sentinel Realistic Product Rules QA

## Reglas añadidas

Sentinel ahora debe detectar si una pantalla deportiva central carga pero no muestra filas ni estado seguro.

Rutas vigiladas:

- `/partidos`
- `/calendar`
- `/live`
- `/directo`
- `/picks`

Estados seguros aceptados:

- Sin partidos reales.
- Esperando proveedor.
- Sin sincronización reciente.
- Requiere sincronización real.
- Proveedor sin datos.
- Sin directos reales.
- Sin picks activos.
- Cuota pendiente.
- Selección pendiente.
- Pick en revisión.
- Sin pick real publicado.

## Resultado esperado

No más “score 10” si el núcleo deportivo está vacío sin explicación visible.
