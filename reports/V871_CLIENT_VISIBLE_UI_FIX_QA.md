# V871 Client Visible UI Fix QA

## Pantallas impactadas
- `/app`.
- `/partidos`.
- `/calendar`.
- `/live`.
- `/directo`.
- `/picks`.
- `/shark`.
- `/telegram`.
- `/profile`.
- `/track-record`.
- `/support`.

## Correcciones visibles
- Menos labels repetidos en navegación.
- CTAs de macros más limpios.
- Telegram con español correcto.
- Botones SHARK pasan de `SHARK` genérico a `Abrir SHARK` donde procede.
- JS base reparado para que interacciones visuales funcionen.

## No inventar datos
Se mantienen estados seguros: `Sin datos reales`, `Esperando proveedor`, `Cuota pendiente`, `Pick en revisión`.
