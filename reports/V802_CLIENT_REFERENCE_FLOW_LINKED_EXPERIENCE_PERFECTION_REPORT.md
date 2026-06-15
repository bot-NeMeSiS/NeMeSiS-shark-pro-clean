# V802 Client Reference Flow Linked Experience Perfection

## Objetivo
Avance centrado en acercar la experiencia cliente al formato de las referencias: app deportiva oscura, flujo claro y pantallas enlazadas.

## Pantallas reforzadas
- Inicio /app
- Calendario / Partidos
- Directo
- Picks
- Detalle de partido
- SHARK / flujo de consulta

## Cambios clave
- Nuevo flujo visual común: Inicio → Partidos → Directo → Picks → Detalle → SHARK.
- Calendario con resumen seleccionado, ligas agrupadas por bloques importantes y foco rápido de partidos visibles.
- Selector de días ampliado a 14 días sin inventar partidos.
- Ligas importantes reordenadas por grupos: España, Inglaterra, Europa, Selecciones, Mundial y más ligas.
- Refuerzo visual de filas de partido, picks conectados y acciones Detalle/SHARK.
- Más sensación de app premium con cards, halos, jerarquía y navegación consistente.

## Regla de datos reales
La versión no crea partidos, cuotas, resultados, ROI ni picks ficticios. Si falta un dato, la pantalla muestra pendiente, sin dato o esperando sincronización.

## No tocado
- DB_PATH
- AUTOMATION_SECRET
- Render Cron
- Telegram real
- usuarios/sesiones
- membresías/pagos
- lógica core de picks
- Madrid Time
