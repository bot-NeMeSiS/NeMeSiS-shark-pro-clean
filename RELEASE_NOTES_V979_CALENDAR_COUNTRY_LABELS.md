# V979 — Localización y horarios fiables en el calendario

Inicio, Calendario, el explorador de competiciones y las tarjetas compartidas muestran los nombres conocidos de países y regiones en el idioma elegido por el usuario. Los filtros conservan sus valores originales para que la búsqueda y la selección sigan coincidiendo con los datos de origen.

Las tarjetas de partidos programados mantienen visible su hora local cuando el proveedor entrega puntuaciones vacías o incompletas. Solo muestran un resultado cuando están presentes los dos marcadores; el cero sigue siendo válido. La actualización en vivo aplica el mismo criterio para no inferir un resultado a partir de un dato parcial.

La traducción solo se aplica a etiquetas geográficas reconocidas. Los nombres desconocidos se muestran tal como llegan; no se cambian identidades, partidos, persistencia, permisos ni llamadas a proveedores.

Validación local inicial del candidato: 108 pruebas aprobadas y 1 omitida por la falta de soporte de enlaces simbólicos en Windows. Una revisión remota encontró una incompatibilidad en el tratamiento de marcadores parciales; el ajuste conserva el contrato previo de no inferir el resultado y mantiene visible la hora programada. Se reejecutaron satisfactoriamente las pruebas focalizadas de tarjeta, calendario y actualización en vivo, junto con `node --check` y `git diff --check`. La suite completa y los controles remotos de la revisión corregida siguen pendientes.
