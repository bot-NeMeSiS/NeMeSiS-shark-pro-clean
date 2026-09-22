# Admin: jornada operativa y acciones verificables — 23/09/2026

## Base y alcance

Base main PR71: `706094630d337f9e329a8401fae217b316a9b49c`, árbol `63fb87401730ace4505b6d2b0102be86b1778972`. Candidato administrativo separado de PR60/vídeos y PR68/estadísticas. No cambia app.py, DB_PATH, proveedores, cron, pagos, usuarios, membresías ni Telegram. No despliegue en esta intervención.

Se reutilizan `/admin/operations-center` y sus cinco nombres de ruta existentes. No se crea otro panel, endpoint ni cola persistente. El dashboard añade «Jornada operativa» sin quitar sus accesos anteriores. El cambio de composición en blueprints/architecture.py añade dos líneas: conservar también el registro de media_review al integrar posteriormente PR60, no sobrescribirlo.

## Trabajo diario

Bandeja construida a partir del snapshot operativo ya existente, sin nuevas consultas, archivos o peticiones externas. Presenta primero hallazgos clasificados como confirmados, después investigación y evidencia pendiente, con prioridad dentro de cada grupo. Esa clasificación proviene del diagnóstico: no es una auditoría independiente ni certifica salud o frescura de proveedores.

Búsqueda por área, título, evidencia y siguiente paso; filtros de categoría/prioridad y directorio de doce herramientas existentes. Los enlaces se toman de una lista interna, no de URLs suministradas por un hallazgo. No se mezclan todos los tickets/colas de otras áreas: el directorio abre sus paneles, mientras la bandeja representa los incidentes de Operaciones.

Cada tarea permite consultar la evidencia y copiar un texto de investigación con su ID, contexto, panel, objetivo y criterio de cierre. Copiar no asigna trabajo, no ejecuta Codex, no marca revisado/resuelto y no activa trabajadores. Sin acceso al portapapeles se ofrece el texto para copiar manualmente; con JavaScript desactivado siguen disponibles tareas, textos y enlaces.

El diagnóstico detallado anterior queda desplegable, no eliminado. Las anclas abren el detalle que las contiene cuando JavaScript está disponible; sin él se conserva el desplegable nativo. No se cambia la fórmula heredada de puntuaciones ni se acredita que todas sus fuentes estén auditadas. La hora mostrada pertenece a la lectura local, no a una observación externa ni a vigilancia 24/7.

Una colección ausente/ilegible no aparece como cero en la nueva bandeja; una lista leída y vacía conserva cero. Filas malformadas y límites de 200 se declaran parciales. IDs repetidos se mantienen separados con aviso, sin fusionarlos automáticamente.

## Reparaciones de comportamiento

La plantilla anterior podía interpretar `section['items']` como el método del diccionario cuando faltaba esa clave; la reproducción HTTP encontró TypeError. Se utiliza get y se protege también el bloque de monitor independiente ausente. Las vistas parciales ya no rompen por esos dos accesos.

Las acciones originales conservaban nextIssue después de ejecutar un diagnóstico, aceptaban cualquier HTTP correcto sin verificar ok y permitían preparar otra acción simultánea. El nuevo controlador valida HTTP/JSON/ok y la identidad del prompt recibido. Un resultado de diagnóstico requiere renovar la bandeja antes de reutilizar acciones; no cambia silenciosamente la lista ni presenta una tarea distinta como la solicitada.

Bloqueo de doble acción en la misma pantalla, espera acotada a 20 segundos y ningún reintento automático. Si el resultado no se puede confirmar, se advierte que la operación podría haber llegado al servidor y se pide revisar antes de repetir. No es un bloqueo entre pestañas ni idempotencia nueva del backend. El backend previo y su auditoría permanecen sin cambios.

Se mantienen las guardas administrativas y los encabezados CSRF de la plataforma. Las respuestas de las páginas de Operaciones y sus APIs son private/no-store con Vary:Cookie. Los helpers solo se inyectan en esas páginas tras autorización. La presentación no se aplica a clientes.

## Pruebas de esta intervención

54 casos nuevos aprobados: 40 de lógica/plantillas/autorización y 14 de Chromium. Incluyen datos ausentes, límites, clasificación, duplicados, enlaces registrados, aislamiento de contexto, rutas administrativas reales con snapshots sintéticos, escape HTML, filtros, copia alternativa, sin JavaScript, respuesta fallida, prompt de otro ID, invalidación y exclusión de solicitudes simultáneas.

144 regresiones heredadas aprobadas de administración, lecturas, Combinadas y catálogo. Total local de dos grupos sin solapamiento: 198 aprobados. No es toda la suite del repositorio. Se recuperaron Flask/Werkzeug/Blinker/Stripe de wheels ya montados, sin descargar dependencias. Las pruebas HTTP conservan el route/render/autorización reales, pero inyectan datos sintéticos y no certifican el catálogo de producción.

Navegador: 320/390/430/1366 px sin desbordamiento en los componentes; no certificación de Safari/iPhone ni del shell completo. Capturas SIMULATED_QA. Transporte de acciones simulado, resto de red bloqueado. Los primeros intentos incompletos por límite de ejecución, el error de plantilla y fallos iniciales de búsqueda se conservan; se corrigió el producto. Dos bloqueos de helpers de navegador se arreglaron en las pruebas nuevas (CSS inline sin JS y función que configura fetch sin devolver una promesa pendiente). Al verificar los blobs se detectó una etiqueta option incorrecta: se corrigió y añadió la prueba del filtro confirmado; se repitió el grupo completo.

Auditor de navegación existente sin cambios: 831 rutas, 1150 entradas, cero rotas/cero botones sin acción; 274 advertencias conservadas. Compilación y sintaxis JS aprobadas; 211 plantillas parseadas y hora Madrid correcta. Escáner existente: 1246 archivos, cero secretos y tres avisos de privacidad conservados. La fuente local es la distribución del CI de PR71, no un clon completo; los tres archivos modificados de base se contrastaron mediante sus SHA nativos y los diez blobs de código/pruebas coinciden con los bytes probados.

## Publicación y pendientes

Exigir QA, Preflight y Smoke normales sobre el HEAD exacto antes de integrar. No forzar merge, alterar umbrales ni provocar otro deploy para documentación. No se han ejecutado acciones productivas, cobros, mensajes, consultas deportivas ni cambios de cuentas. Las capturas y la prueba del diagnóstico no acreditan una ejecución administrativa real en Render.

Quedan separados: revisión de todos los indicadores heredados, permisos reales de los futuros operadores, gestión/contestación de soporte y medición de tiempos con usuarios. Este bloque reduce dispersión y protege el uso del centro existente; no afirma automatización total, cierre de incidencias por sí solo ni operación continua certificada. Vídeos y estadísticas conservan sus pendientes propios.
