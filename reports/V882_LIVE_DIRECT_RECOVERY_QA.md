# V882 Live Direct Recovery QA

## Revisión

- `/live`: 200 local con DB temporal.
- `/directo`: 200 local con DB temporal.
- Si no hay directos, se mantiene “Sin directos reales ahora mismo”.
- Se preservan estados de minuto/marcador solo si el dato existe.
- No se inventan resultados, eventos ni minutos.

## Fix seguro

V882 no fuerza sync live ni llamadas API. Refuerza el contrato de estado vacío: proveedor/cache/guard visibles y Sentinel preparado para marcar ausencia sin explicación.
