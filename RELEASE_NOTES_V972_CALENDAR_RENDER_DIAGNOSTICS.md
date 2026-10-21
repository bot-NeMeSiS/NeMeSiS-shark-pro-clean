# V972 — Diagnóstico por etapas del calendario

V972 expone `Server-Timing` por etapa en la vista de calendario para separar el tiempo de contexto deportivo, resultados históricos, preparación de la agenda, contexto de directo y renderizado HTML. Las medidas son efímeras por petición, no guardan información del usuario y no realizan llamadas a proveedores ni escrituras en SQLite.

La respuesta mantiene la misma estructura y contenido. La versión permite localizar con evidencia de producción qué etapa explica la latencia observada antes de aplicar una optimización y medirla.

Validación local del 21 de octubre de 2026: 16 suites de calendario, resultados, presentación responsive y control de navegador superadas; identidad de versión alineada en `app.py`, `APP_VERSION` y `VERSION.txt`; compilación de `app.py` correcta. No se hicieron llamadas a proveedores ni escrituras de datos. La validación de Render y la lectura de los tiempos por etapa quedan pendientes de la publicación automática.
