# V762 Client Screen QA Notes

## Revisión aplicada
- Inicio cliente: debe leer "Partidos de hoy y próximos" y "Picks activos destacados".
- Partidos: cada fila debe decir día, hora Madrid, equipos, competición y estado.
- Picks: cada fila debe decir partido, competición, hora Madrid, selección, mercado, cuota y riesgo.
- Calendario: no debe mostrar instrucciones internas de admin/Cron.
- Live: debe separar directo, finalizado y próximo.
- Detalle partido: debe mostrar día y hora Madrid, no solo la hora.

## Criterio comercial
El cliente no debe necesitar adivinar de qué partido es un pick ni cuándo se juega. Si falta cuota o mercado, se avisa sin inventar.
