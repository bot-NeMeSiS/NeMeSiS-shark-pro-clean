# V1000.2 · interpretación local de nombres deportivos

El motor de presentación analizaba dos veces el mismo nombre de equipo: al derivar sus evidencias y al contrastarlo con el payload original del proveedor. También ejecutaba expresiones regulares para categorías exactamente vacías.

Cada derivación fresca conserva ahora sus formas inmutables del nombre, exclusivamente para contrastar ese mismo texto `str` exacto dentro de su payload. Un texto distinto, un alias u otro tipo de valor sigue el recorrido anterior. La categoría ampliada, los identificadores ordenados, competición, temporada, deporte y fecha siguen verificándose. Los nuevos metadatos privados no participan en igualdad o representación y conservan la construcción anterior de cuatro argumentos.

La proyección actual de identidad y su comprobación por cada consumidor no cambian. No se conservan identidades, grupos o ganadores entre filas, selecciones o peticiones. Los objetos personalizados y subclases mantienen el comportamiento del normalizador anterior; el atajo de categoría vacía se limita a primitivos exactos o al resultado ya vacío de ese normalizador.

El prototipo pasó 287 casos aislados bajo el guard original LOCAL SAFE, incluidos 74 contrastes contra el motor completo de la base publicada, 55 casos nuevos de la optimización y regresiones de agrupación, mutaciones, asociaciones financieras y combinadas. El motor anterior congelado y el diagnóstico permanecen como evidencia externa de QA, sin introducir otra implementación productiva. Los grupos de pruebas solapados no deben sumarse como cobertura distinta.

En dos procesos separados con los mismos datos sintéticos, el contexto de Calendario para 240/800/3200 partidos pasó de 970/3186/14350 a 718/2472/11087 ms. En el caso mayor se conservaron las 28800 comprobaciones actuales de identidad, los recuentos y el digest de entrada. La base SQLite y las fuentes no cambiaron durante las pruebas. Es una muestra local del contexto, sin cProfile; no acredita la latencia del endpoint completo ni rendimiento frío o productivo. El timeout observado en producción sigue abierto hasta verificar la versión servida.

No cambia esquema, persistencia, datos reales, permisos, presupuestos, cuotas, proveedores, pagos, mensajes, servicios o disco. La publicación exige revisión del HEAD final, CI aplicable, integración autorizada y verificación posterior. Backup real, recuperación aislada, cobertura completa y cierre integral de v1 siguen pendientes.
