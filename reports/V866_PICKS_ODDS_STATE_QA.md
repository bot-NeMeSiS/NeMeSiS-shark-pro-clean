# V866 picks odds state QA

## Problema
Los picks sin cuota podían verse con un texto demasiado genérico y poco comercial.

## Corrección aplicada
`enrich_pick_client_context()` separa estados visibles:
- `Cuota pendiente`.
- `Selección pendiente`.
- `Pick en revisión`.
- `Sin pick real publicado`.
- `Proveedor sin datos ahora mismo`.

## Reglas
- Una cuota ausente, cero, `None`, `null`, `undefined` o `NaN` no se muestra como cuota real.
- Una selección ausente se muestra como `Selección pendiente`.
- Un pick incompleto no se presenta como pick premium final.
- No se inventa ROI, confianza, stake, cuota ni selección.
