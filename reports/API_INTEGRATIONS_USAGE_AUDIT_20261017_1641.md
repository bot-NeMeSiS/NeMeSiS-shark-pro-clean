# Auditoría de aprovechamiento de integraciones — 17 octubre 2026, 16:41 Madrid

## Resultado principal

La suscripción de **API-Football Pro está activa y pagada**. El panel autenticado muestra 27 solicitudes usadas de 7.500 diarias, vigencia hasta el 17 de noviembre de 2026 a las 09:49:48 UTC y una compra Pro de un mes por 19 USD completada el 17 de octubre. No es un plan Free. La cuota consumida equivale al 0,36% del límite diario; el saldo de 7.473 es un cálculo a partir del contador del panel.

La página oficial confirma que Pro permite 7.500 solicitudes al día y 300 por minuto, con todos los endpoints; la diferencia del plan Free es principalmente su cuota y la limitación de temporadas. El proveedor recomienda consultar la cobertura por competición/temporada y agrupar IDs de partidos cuando se solicitan detalles, para no gastar llamadas innecesarias: [planes oficiales](https://www.api-football.com/pricing), [optimización de llamadas y cuotas](https://www.api-football.com/news/post/how-to-optimize-api-sports-calls-and-quota-usage), [condiciones de suscripción](https://www.api-football.com/terms).

## Qué está funcionando ahora

- **Directo:** el panel del proveedor registra llamadas recientes cada cinco minutos a `fixtures?live=all&timezone=Europe/Madrid`. Los tres ticks naturales observados a las 16:30, 16:35 y 16:40 Madrid terminaron con Sports PASS, HTTP 200, una llamada y cero errores técnicos. La respuesta del carril directo fue marcada como observación vigente en los tres.
- **Calendario y resultados:** la ruta primaria está configurada, pero esos tres ticks reutilizaron caché, sin petición nueva. Su última observación registrada es 14:15:37 Madrid; a las 16:40 tenía unas 2 h 25 min. El caché está configurado para seis horas, así que no se puede llamar todavía un fallo de actualización, pero sí conviene revisar si esa cadencia basta para próximos partidos y cambios de calendario.
- **Datos detallados:** el último muestreo profundo registrado fue a las 15:25 Madrid, utilizó siete llamadas para un partido seleccionado y recibió eventos, H2H, lesiones, alineaciones, clasificación y estadísticas. En los tres ciclos recientes la etapa profunda figuró `SKIPPED_NOT_DUE`; esto conserva cuota, pero significa que no se renuevan detalles de cada partido en cada ciclo.
- **Claves:** el código de `origin/main` toma la clave de variables de entorno del servidor y no se encontraron referencias a `API_FOOTBALL_KEY` ni `x-apisports-key` en JavaScript estático o plantillas. No se mostró ni se copió la clave.

## Oportunidades y prioridad

1. Mantener el refresco global de directo cada cinco minutos como base y evaluar, con autorización antes de producción, una frecuencia menor solo durante ventanas con partidos en vivo. El panel oficial dice que los datos de fixtures/eventos pueden actualizarse más a menudo; la app tiene un único Cron cada cinco minutos. No propongo cambiarlo ahora: la memoria Render subió de 350 MB a 448 MB en la última hora, aproximadamente el 83,4% del límite observado.
2. Mejorar el refresco de calendario de competiciones seguidas y próximas, en vez de consultar indiscriminadamente todas las temporadas. Confirmar primero `coverage` por liga y temporada.
3. Aprovechar alineaciones, eventos, estadísticas, lesiones, clasificación e historial solo para partidos/ligas con cobertura disponible y valor de usuario. El último muestreo detallado se concentró en un partido; hay margen para priorizar los próximos partidos destacados y favoritos.
4. Revisar batching de IDs en el enriquecimiento: el proveedor documenta respuestas agrupadas para evitar repetir llamadas de eventos, alineaciones y estadísticas partido a partido. Preparar cambios localmente y medir llamadas/resultados en pruebas aisladas antes de proponer su publicación.
5. Mantener visible en el Centro de Mando la hora y vigencia del plan/cuota. El contador guardado por la app (5/7.500 a las 15:25) ya es histórico frente al panel actual (27/7.500 a las 16:41); no presentarlo como saldo vigente.

## Otras integraciones en los últimos ciclos naturales

| Servicio | Observación | Estado real que puede afirmarse |
|---|---|---|
| The Odds API | `CACHE_REUSED`, cero llamadas externas, observación no vigente; el 439 restante es histórico. | No se ha comprobado conexión/cuota actuales. |
| TheSportsDB | Highlights `PARTIAL` y postmatch `PARTIAL`; cero llamadas externas en el último tick, dos elementos procesados. | Hay trabajo local de cola, pero no una observación fresca del proveedor en ese tick. |
| Telegram | El runner devolvió `OLD_MATCH` con HTTP interno 200. | No demuestra un mensaje nuevo entregado; no se envió ninguno manualmente. |
| Stripe | La conexión del conector solicita reautenticación. | Estado de la cuenta Stripe y pagos no verificados en esta revisión. |
| Render | Web y Cron en producción LIVE en `09e772f51030ddb128b79aeeded247b7857e866c`; última ejecución Cron exitosa 16:40:40 Madrid. | Servicio activo. La memoria mostró una subida que conviene vigilar antes de aumentar la frecuencia de tareas. |

## Límites de esta revisión

La consola del proveedor se consultó en lectura; la revisión de cuota no ejecutó una llamada API. Los ciclos del Cron ocurrieron de forma natural. No se cambió ningún plan, secreto, pago, dato, frecuencia de producción, servicio ni despliegue. El estado de The Odds API, TheSportsDB y Telegram se basa en recibos recientes de la app, no en una cuenta autenticada de esos proveedores. Stripe no pudo leerse porque su conexión requiere reautenticación.
