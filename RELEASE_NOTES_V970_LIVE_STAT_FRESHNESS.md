# V970 — Frescura de estadísticas en Directo

Directo actualiza las estadísticas disponibles dentro del refresco existente del marcador, sin recargar la página ni realizar llamadas nuevas a los proveedores. Cada valor conserva su hora real de recepción por equipo; si una respuesta omite una métrica, se mantiene su último valor con su hora original. Las capturas sin valor no sustituyen datos válidos y las fechas futuras o no verificables no se presentan como recientes.

La lectura de estadísticas se agrupa por partido y expone solo los campos necesarios para la tarjeta. Valores ausentes, marcadores de texto, booleanos, estructuras y números no finitos no sustituyen datos válidos; el recibo original del proveedor se conserva en el archivo de observaciones. La posesión usa la hora propia de esa métrica, así que una estadística más reciente no invalida ni rejuvenece el gráfico. Las capturas con más de diez minutos se marcan como retrasadas.

El indicador estimado de actividad aparece solo mientras sus dos valores estén disponibles y se oculta correctamente cuando dejan de estarlo. Sigue identificado como una estimación de NeMeSiS, nunca como métrica oficial, localización del balón o mapa de zonas. La caché SQLite conserva las observaciones históricas y las estadísticas actuales; las muestras vacías no borran valores útiles ni renuevan su antigüedad.

Validación local: pruebas de ingestión, selección temporal, endpoint de solo lectura y recorrido de navegador de Directo en escritorio y móvil. La prueba confirma actualización sin recarga, misma tarjeta y foco, rechazo de repeticiones manipuladas, retención de valores omitidos y ausencia de llamadas externas.
