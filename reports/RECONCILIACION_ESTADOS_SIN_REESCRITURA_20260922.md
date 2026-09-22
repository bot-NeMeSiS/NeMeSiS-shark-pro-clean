# Ciclo de vida: conservar evidencia del proveedor

Candidato añadido a PR64; no publicado. Reconciliación sobre main PR66 `666f0580c7d036606921d08e368be8d14888ab93`. Conserva presupuesto atómico, transacciones cortas y pruebas anteriores de PR64. No modifica Combinadas, plantillas, app.py, cuotas, cuentas, pagos ni envíos.

## Defecto y decisión de arquitectura

La función heredada `reconcile_match_lifecycle` escribía Finalizado cuando encontraba cualquier marcador y Resultado pendiente para estados pasados que no coincidían con exclusiones de texto. Las reproducciones con base temporal confirman que esto destruye NS con cero provisional, HT y códigos de proveedor, aplazados/cancelados y sus fechas updated_at.

La corrección utiliza `match_status_truth` y **deja de reescribir status y relojes de matches**. Es un cambio deliberado de contrato: esta tarea ahora hace diagnóstico canónico de solo lectura; no normaliza etiquetas en la tabla de origen. Las vistas ya tienen el motor de clasificación común. La sincronización autorizada conserva la responsabilidad de escribir datos nuevos del proveedor.

No se inventa una corrección de filas antiguas que ya estén dañadas. Para recuperarlas hará falta evidencia original o una nueva recepción autorizada. Un marcador provisional no es prueba de finalización; un partido sin resultado que ya empezó puede presentarse como pendiente sin reemplazar para siempre su estado fuente.

## Operación y compatibilidad

Se mantienen nombre, firma y claves legacy updated (sus tres contadores son cero: no hubo actualizaciones). Los resultados observados van a lifecycle_counts, assessed, status_conflicts y samples. La operación no crea el archivo si falta, no migra esquema ni escribe tablas. SQLite mode=ro/query_only y cierre explícito.

Se evalúan como máximo 200 registros ordenados por ID local descendente y se incluyen hasta 20 muestras en el informe. truncated indica que quedan más; complete_database_audit permanece false. No es auditoría de toda la temporada ni selector de prioridad deportiva. No devuelve payloads originales ni consulta proveedores.

La ejecución a través del master mantiene el registro de auditoría del trabajo en las tablas de automatización existentes; ese registro no se confunde con una modificación deportiva. Errores de almacenamiento se marcan como error, no como catálogo vacío correcto. La fecha del diagnóstico se normaliza a Madrid incluso si el reloj de entrada es UTC.

## Pruebas de esta ampliación

Selección local final: **60 casos distintos aprobados**, cero fallos/errores/omisiones. Incluye **28 nuevos** y 32 regresiones de las transacciones y el guard de API anteriores. Son bases y partidos sintéticos, no pruebas en producción.

Quince variantes de estado, cero válido frente a ausencia, señales contradictorias, directo caducado, cambio de hora manteniendo el registro fuente, integridad byte a byte de SQLite, no creación/migración, SQL sin mutaciones, muestra truncada, fecha Madrid y recorrido a través del master con auditoría conservada. Las conexiones de red se bloquean en los tests nuevos.

Se preserva un pase previo de 27 fallos de los 27 casos disponibles entonces contra el reconciliador antiguo, incluido el defecto de estado y el contrato anterior de escritura. La prueba adicional del master se añadió después: no se le atribuye un fallo previo que no se ejecutó.

Compilación de los Python intervenidos, check_v818_match_lifecycle_automation y check_madrid_times: aprobados. No se ha modificado ningún test heredado, workflow ni umbral. La selección local procede del código PR63 con PR64 aplicado; CI debe certificar el árbol reconciliado con main completo.

## Puertas que siguen abiertas

Mantener PR64 en borrador hasta revisar CI del HEAD ampliado y compatibilidad operativa. No habilitar hilos ni afirmar exactamente una ejecución global: ALWAYS/force y concurrencia del cron real conservan revisión propia. Esta tarea heredada no es el runner productivo de cinco minutos. No demuestra desaparición de 502 ni aceleración del móvil.

PR66 ya se publicó por separado; no interrumpir su observación con otro merge. Estadísticas históricas, vídeos y cobertura de proveedores siguen pendientes independientes. No se han modificado datos de producción ni ejecutado pagos, apuestas, Telegram o consultas deportivas para validar este candidato.
