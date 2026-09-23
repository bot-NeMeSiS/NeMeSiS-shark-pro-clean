# Archivo estadístico e integración de recepción — candidato de 22/09/2026

## Identidad y alcance

Base verificada: main PR64 `454c3ca1abb79af6a8525f65daecc57c0958c0c1`, árbol `49f3016e1378ae61d6260b5631ca550eed04f5d5`. Nueve archivos: dos ingestors modificados, archivo nuevo, dos herramientas internas, tres módulos de pruebas y este informe. No altera app.py, plantillas, rutas públicas, cron, proveedor contratado, cuotas, pagos, usuarios ni Telegram. Conserva Combinadas y las reparaciones publicadas. No integra PR59/60 ni el lector de Match Center cuya escritura quedó bloqueada; no se ha reenviado ese lector por otra vía.

## Archivo conectado a la recepción existente

`record_observation` conserva respuestas ya recibidas de API-Football por fixture numérico y sección: fixture, statistics, events, lineups y players cuando esta última viene incluida. Estadísticas, eventos, alineaciones y metadatos se anexan sin sustituir las versiones anteriores. Vacío recibido correctamente es una observación; un error no es vacío ni cero. Se conservan los valores nulos y los ceros, correcciones de acumulados, cambios de asistencia y retirada de eventos.

Identidad de proveedor, hora UTC de recepción, contexto conocido, JSON comprimido e integridad SHA-256. La hora corresponde a recepción NeMeSiS, NO a publicación del proveedor. Sin relleno retrospectivo del minuto ni reconstrucción de lo no recibido. No hace consultas deportivas adicionales para obtener campos ausentes. Las tablas de caché actuales siguen funcionando; su lectura por la ficha NO se cambia en este bloque.

Esquema aditivo creado durante ingestión dentro de la transacción existente, sin commits autónomos. Límite de payload 512 KiB; presupuesto 64 MiB de payload/contexto codificados y 100.000 observaciones; no equivale al tamaño físico SQLite, WAL o índices ni a capacidad infinita. No borra historial automáticamente. Al alcanzar límites, registra carencia y permite que la caché actual continúe. Contabilidad no verificable se distingue de lleno/vacío y no se repara inventando cifras. La verificación numérica no reconcilia todas las filas.

Las escrituras se confirman por sección antes de la siguiente petición HTTP. Un fallo posterior conserva las secciones ya terminadas; un rollback revierte la sección pendiente y su reserva. Se prueba SQLite DELETE/WAL, capacidad compartida por hilos y conexiones independientes durante I/O simulado. Esto NO habilita concurrencia global, multiplica workers ni promete exactly-once entre todos los procesos.

## Correcciones de recepción

- La agenda llamaba a dos funciones inexistentes al recibir partidos; ahora reutiliza `_upsert_fixture`, el guardado real de LIVE.
- Una respuesta LIVE marcada `ok=False` podía contener filas y producir nuevas escrituras y dos consultas de profundidad. Ahora no se acepta ese contenido ni se lanzan esas consultas por él. Los datos previos permanecen. Dos regresiones fallaban antes y pasan con la corrección.
- La agenda declaraba OK después de recibir un fixture aunque eventos/estadísticas fallasen. Ahora informa PARTIAL con categoría de fallo, conserva la sección correcta y no archiva un vacío ficticio para la rechazada. Tres regresiones fallaban antes y pasan ahora.
- JSON con sección de tipo incorrecto no se trata como una lista vacía correcta; `/status` conserva su respuesta tipo objeto. Los fallbacks, intervalos de caché, backoff y límites de llamadas existentes no se aumentan ni se saltan.

La estructura histórica de estados de todos los endpoints no se ha rediseñado: algunos conservan ok del trabajo junto a status parcial. Los consumidores deben seguir comprobando status/errores. No se afirma que el acceso API-Football esté resuelto ni que se hayan recibido datos de cada liga.

## Inspección y reproducción internas

`tools/inspect_match_record_archive.py` exige una base local explícita y fixture API-Football, lee mode=ro/query_only y admite `--as-of` con timestamp consciente. Sin migración, HTTP o endpoint público. `--include-payload` es interno; no autorización de redistribución.

`python tools/reproduce_match_record_history.py` crea únicamente una base temporal sintética. Cierra/reabre para consultar revisiones: córners 0/3/2, eventos 0/1/0, observaciones 2/4/6, saques ausentes null. No suma acumulados ni filtra conocimiento posterior hacia el pasado. Cero intentos de conexión externa. No es recepción productiva ni prueba de toda una temporada.

## Validación local final

**175 casos distintos PASS, cero fallos/errores/omisiones** en la selección ampliada. Incluye los 91 del candidato anterior, 5 nuevos de esta intervención y 79 regresiones existentes relacionadas. Los 119 del pase enfocado se solapan y no se suman. La PR añade 96 casos frente a main, no 175 nuevos. No es toda la suite ni QA visual de Safari/PWA.

Se conservaron los pases negativos: dos fallos en la aceptación de respuesta LIVE rechazada, y tres fallos posteriores de reporte parcial de profundidad (los dos primeros ya pasaban). Se eliminaron únicamente un mock redundante en una prueba nueva de este candidato; ninguna aserción, expectativa heredada, workflow o umbral se ha rebajado. El pase final utiliza los bytes exactos subidos.

Compilación de los ocho Python, hora Madrid y reproducción interna PASS. Escáner existente: 1.230 archivos, cero hallazgos de secretos, dos avisos previos de privacidad conservados. Red bloqueada en los nuevos tests; transporte del proveedor simulado. Cuentas/DB de pruebas temporales.

La fuente local procede de la distribución CI63 más parches publicados65/67/66/64: no equivale a clonar y probar íntegramente el árbol remoto actual. Los originales de los dos ingestors coinciden con sus blobs main `fbbdb977b817967ae925602f33c38178d1c400a6` y `e24c535e08cf8826a9e0bf820f9eea816edf06a4`. El CI normal debe validar el árbol reconciliado exacto.

## Puerta de integración y pendientes

Candidato para PR en borrador, NO desplegado al redactar este informe. Exigir QA, Preflight y Smoke completos, revisar capacidad disponible/licencia de retención y conservar la observación de producción activa PR64 `35718992463`. No cancelar esa observación, eludir controles ni realizar un deploy manual duplicado.

Este bloque conserva datos recibidos; NO activa una nueva pestaña estadística ni corrige los lectores históricos de la ficha, ni garantiza última revisión visible. Faltan lectura autorizada de Match Center, recepción real/cobertura del proveedor y validación del circuito cliente completo. No se han forzado llamadas, limpiado caché productiva, cambiado claves/plan ni solicitado pagos. No se han colocado apuestas ni enviado Telegram. No presentar «archivo implementado» como «todas las estadísticas disponibles en producción».


## Guardia física de disco añadida al refrescar sobre main actual

Además del límite lógico de 64 MiB/100000 observaciones, el candidato conserva ahora una
reserva mínima de 128 MiB libres en el filesystem que contiene SQLite. Si una nueva
observación dejara el disco por debajo de esa reserva, solo se omite ese append y se
registra `DISK_RESERVE_REACHED`; la caché/ingesta normal sigue su contrato. La salud
expone bytes libres, reserva y estado `OK/LOW/UNKNOWN`, nunca la ruta del filesystem.
La medición es local al host y best-effort: `UNKNOWN` no se presenta como espacio
suficiente. Esta protección no sustituye la monitorización del disco completo ni afirma
que 64 MiB sean el tamaño físico máximo de SQLite, índices o WAL.
