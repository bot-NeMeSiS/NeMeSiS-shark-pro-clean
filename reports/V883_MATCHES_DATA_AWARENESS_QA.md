# V883 Matches/Data Awareness QA

El worker revisa rutas deportivas y exige estados seguros cuando no hay datos reales.

## Rutas cubiertas
- `/partidos`
- `/calendar`
- `/live`
- `/directo`
- `/picks`
- `/track-record`
- `/app`

## Reglas aplicadas
- No inventar partidos.
- No inventar picks.
- No inventar cuotas.
- No inventar resultados.
- No inventar minutos.
- No inventar escudos oficiales.
- Si faltan datos, mostrar estado seguro y tarea admin.

## Resultado esperado
Cuando una pantalla deportiva no tiene filas/cards ni estado seguro visible, el worker crea issue high y prompt Codex especifico.
