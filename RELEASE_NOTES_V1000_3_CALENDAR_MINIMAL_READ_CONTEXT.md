# V1000.3 — preparación exclusiva del Calendario

El Calendario preparaba Home, métricas repetidas y paneles de pronósticos/cuotas sin consumidores en esta página. Ahora solicita una proyección explícita de preparación y conserva su contexto completo de partidos, grupos, fechas, filtros, favoritos, proveedor y métricas visibles. La fecha se normaliza con la pestaña solicitada antes de preparar identidad e historia.

La opción es privada y solo se activa en la ruta HTML del Calendario. Home, API, Directo, SHARK y el modo no compacto conservan sus recorridos. Se mantienen bloqueo/degradación, usuario actual, permisos y CSRF, referencias acotadas y las verificaciones frescas C1/C3. No cambia esquemas, datos, límites de filas, plazos, llamadas autorizadas, presupuestos, proveedores, derechos ni configuración de Render.

Validación local previa a alinear la etiqueta: 238 casos, incluidos 21 nuevos, bajo el guard original; worker real separado con 13 contratos. Seis GET WSGI adicionales verificaron usuario anónimo/FREE/ADMIN, historia, fechas y favoritos aislados, más rechazo real de un POST sintético sin CSRF. Los grupos no se suman. El contraste pasivo de 800 admitidos conservó C1, referencias y 1622 selecciones C3 del Calendario; comprobó la copia de presentación y los mismos IDs, orden y grupos. Home 2→1, métricas 9→3 y proveedor 3→1 en esa muestra fría local.

Muestras locales separadas sin perfilador: 14.325→7.380 ms con el mismo digest de semántica visible; una observación por proceso y SQLite propio, relojes de siembra y cachés del host variables. No acredita rapidez fría/global o productiva. El constructor legado de aceptación de caché fría permanece. sports_metrics.sports_quality queda vacío porque requiere Home y no se muestra en Calendario: no hay equivalencia total de ese payload.

Se conservan los FAIL originales de QA y sus sucesores: identidad de objetos tras la copia real de presentación, y representación false/0 de un flag desactivado por App. Las correcciones afectan al observador, nunca al guard o a C1/C3. La versión final requiere repetir sus contratos exactos y CI aplicable antes de integrar. Publicación, runtime y ciclos naturales se acreditan fuera de esta nota.

Backup real, manifiesto/hash/integridad, recepción durable y restore aislado siguen pendientes. No hay nueva contratación, exportación de datos reales, cambio de disco/coste ni certificación del programa completo.
