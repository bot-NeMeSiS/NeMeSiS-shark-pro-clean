# V884 Core Sports Functionality QA

## Pantallas core

- /partidos
- /calendar
- /live
- /directo
- /picks
- /track-record

## Reglas preservadas

- No inventar partidos.
- No inventar picks.
- No inventar cuotas.
- No inventar resultados.
- No inventar minutos.
- No inventar ROI.
- Si falta dato real, usar estados seguros.

## Mejora V884

Visual Company Worker diferencia:

- pantalla deportiva vacia sin estado seguro: incidencia high;
- pantalla deportiva con estado seguro pero sin filas reales: incidencia low y tarea admin.

## Estado de producto

La app queda honesta: si no hay dato real visible, no rellena con contenido falso. Aun asi, se genera tarea para revisar proveedor, cache, filtros y sincronizacion.
