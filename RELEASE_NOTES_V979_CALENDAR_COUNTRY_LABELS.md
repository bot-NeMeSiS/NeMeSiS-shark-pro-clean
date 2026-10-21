# V979 — Localización y horarios fiables en el calendario

Inicio, Calendario, el explorador de competiciones y las tarjetas compartidas muestran los nombres conocidos de países y regiones en el idioma elegido por el usuario. Los filtros conservan sus valores originales para que la búsqueda y la selección sigan coincidiendo con los datos de origen.

Las tarjetas de partidos programados mantienen visible su hora local cuando el proveedor entrega puntuaciones vacías. Un cero sigue siendo un marcador válido y los marcadores parciales se presentan sin convertirlos en un partido pendiente, también tras una actualización en vivo.

La traducción solo se aplica a etiquetas geográficas reconocidas. Los nombres desconocidos se muestran tal como llegan; no se cambian identidades, partidos, persistencia, permisos ni llamadas a proveedores.

Validación local del candidato: 108 pruebas aprobadas y 1 omitida por la falta de soporte de enlaces simbólicos en Windows; `py_compile`, `node --check` y `git diff --check` aprobados. La suite completa, los controles remotos de CI y la producción quedan pendientes de sus gates propios.
