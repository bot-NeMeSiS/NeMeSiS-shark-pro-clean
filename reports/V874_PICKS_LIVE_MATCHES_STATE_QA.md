# V874 Picks Live Matches State QA

## Revisión

Se revisaron `/picks`, `/live`, `/directo`, `/partidos`, `/calendar` y widgets de `/app` a nivel estático.

## Estados preservados

- `Cuota pendiente`
- `Selección pendiente`
- `Pick en revisión`
- `Sin pick real publicado`
- `Proveedor sin datos ahora mismo`
- `Sin directos reales`
- `Resultado pendiente`

## Reglas

No se muestran cuotas `None`, `null`, `undefined` o `0` como cuota real. No se inventa ROI ni selección.

