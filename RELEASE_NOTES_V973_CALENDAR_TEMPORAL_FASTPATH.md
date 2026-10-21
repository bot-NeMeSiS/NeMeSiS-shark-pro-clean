# V973 — Menos recálculos al mostrar el calendario

Las tarjetas del calendario reutilizan la fecha, la hora y la etiqueta de Madrid preparadas para la petición. Antes, cada tarjeta volvía a normalizar esos valores al dibujarse y el agrupador repetía parte del trabajo. V973 conserva el mismo contenido, orden, horarios y reglas; evita esas conversiones redundantes y mantiene las etiquetas localizadas.

La ruta ya mide sus etapas con `Server-Timing` desde V972. La referencia de producción del 21 de octubre tuvo dos muestras correctas de Calendario: 6,11 y 7,14 s de trabajo de aplicación, con 2,59 y 2,03 s en la plantilla. La página contenía 228 partidos y 90 competiciones en una de las muestras. Son pocas lecturas y no bastan para declarar una mejora global. La publicación de V973 se medirá con el mismo método antes de atribuirle un cambio de rendimiento.

Validación local: regresiones de calendario con horarios Madrid, historial, filtros y contrato de ruta. El render de las tarjetas falla la prueba si vuelve a invocar los formateadores que ahora reciben etiquetas preparadas.
