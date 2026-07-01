# V875 Picks Live Product State QA

## Reglas verificadas

- Picks sin cuota deben mostrarse como `Cuota pendiente`.
- Picks sin seleccion deben mostrarse como `Seleccion pendiente`.
- Picks incompletos deben quedar en `Pick en revision`.
- Live sin proveedor o sin eventos debe mostrar `Sin directos reales` o `Proveedor sin datos ahora mismo`.
- No se debe mostrar `None`, `null`, `undefined`, cuota `0` falsa ni ROI inventado.

## Estado V875

Se mantiene el guard de datos reales y cache-first. No se hacen llamadas API por render.

