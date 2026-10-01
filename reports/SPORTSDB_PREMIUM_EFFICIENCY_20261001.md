# TheSportsDB Premium: aprovechamiento verificable

Fecha: 2026-10-01. PR #138. Base main: `1690df66d3a114df36f9d93df3cb2e2230023afc`.
Solicitud: aprovechar la suscripción Premium existente del usuario (9 €/mes según su confirmación), sin contratar nuevos servicios.

## Cambios de producto

1. El lote pospartido comparte respuestas verificadas en memoria entre sus trabajos. La clave de caché incluye proveedor, huella de credencial, método y parámetros; devuelve copias independientes. No reutiliza caché entre ejecuciones ni renueva artificialmente la antigüedad de datos live. En el caso de regresión de estadísticas + vídeo para un partido se pasa de 3 consultas a 2, conservando todas las aserciones de contenido y revisión. No se extrapola ese ahorro a toda la factura ni al consumo global.
2. El recolector ACTIVO `engines/sportsdb_highlights_engine.py` detecta una respuesta diaria de 50 elementos y solicita particiones por liga, dentro de un presupuesto limitado. Cubre primero las fechas y después alterna las competiciones. No confunde identificadores numéricos de API-Football con los de TheSportsDB. Evita que un enlace vacío bloquee un vídeo posterior válido. No se modifica el duplicado histórico de raíz.
3. Las llamadas externas del recolector no mantienen abierta una transacción de escritura SQLite. Conserva lo ya guardado cuando llega al límite y comunica ejecución completa, parcial o fallida con causas cerradas, sin URL/clave/mensaje privado del proveedor.
4. Un intento fallido del trabajo diario ya no bloquea toda la jornada: puede reintentarse después de 15 minutos. Una colección terminada con límites de cobertura no se vuelve a descargar en cada tick. Se elimina la reconstrucción duplicada del enriquecimiento. Los reintentos por partido siguen perteneciendo a los trabajadores pospartido existentes.
5. El fallback deportivo general obtiene el directo antes del abanico de ligas. Conserva la precedencia del dato live en el normalizador existente y tiene un presupuesto cooperativo de tiempo y número de llamadas. No sustituye la política de relevancia ni los contratos de identidad.
6. La búsqueda pospartido convierte la hora local Madrid a la fecha UTC de consulta. La asociación del recolector convierte timestamps del proveedor a Madrid y exige competición en comparaciones entre proveedores. No se asocian partidos por un número externo sin contexto.
7. El texto diferencia enlaces recibidos pendientes de revisión de ausencia de enlace almacenado. La publicación sigue exigiendo los controles de derechos existentes; descargar metadatos no verifica reproducción.

## Límites operativos

- Recolector highlights: máximo 12 llamadas por invocación, 18 segundos de presupuesto cooperativo y timeout de transporte de hasta 4 segundos dentro del contexto. Fallback general: máximo 10 llamadas. Un deadline cooperativo no es un watchdog de tiempo absoluto para DNS/SO/transporte.
- Estos son límites POR OPERACIÓN; no constituyen un limitador global de toda la cuenta. Los límites compartidos de los trabajadores pospartido no se retiran.
- No se añade ningún Cron ni trabajador. No se habilita V2 por la sola presencia de una clave; se conserva la bandera existente.
- No se afirma cobertura total del proveedor, reproducción de YouTube, un porcentaje de aprovechamiento ni acceso Premium verificado.
- La recuperación de lectores y diagnósticos read-only de #137 es trabajo separado: no se sobrescribe su rama ni se declara integrada aquí. El motor de enriquecimiento histórico no referenciado por app.py no se presenta como mejora activa.
- Sin modificaciones a secretos, planes, pagos, usuarios, pronósticos ni envíos reales de Telegram. Sin despliegue ni activación de los trabajadores de producción, que estaban pausados en la base.

## Evidencia comprobada

Código de producto aplicado: `7266302aabbae5f12f3ebafe89a6aed11d310d54`.
Run `36881312570`, artifact `11171277900`, ZIP SHA256 `5516df347fcb7f0589a04be7719dfa25aa18e592ac0443480f3ec31801cea0e8`.

- 236 casos ejecutados: 41 nuevos + 195 regresiones existentes. Cero fallos, errores y omitidos, confirmado leyendo el XML descargado, no únicamente el estado del workflow.
- Incluye Flask real, rutas protegidas, recuperación pospartido, derechos y revisión, deduplicación, identidad, Match Center, Cron/master tick y copia de seguridad.
- Compilación y análisis de todas las plantillas Jinja en el entorno CI correctos; Madrid Time correcto.
- Cinco archivos modificados mediante parche con SHA256 antes/después para preservar los saltos de línea y no sustituir app.py completo. La única expectativa heredada cambiada es el número de consultas 3→2, justificado por la deduplicación probada.
- En entorno local sin Flask: 41 pruebas nuevas correctas; 46 de recuperación correctas y dos deseleccionadas explícitamente por requerir Flask. Esas dos sí están incluidas en las 236 de CI.
- No se certifican por este XML navegador completo, compatibilidad con ramas no fusionadas ni producción real. Los controles del HEAD después de retirar el auxiliar deben comprobarse separadamente.

## Antes de activar en producción

Integrar únicamente tras comprobar el HEAD final y la convivencia con #137. Tras un despliegue autorizado, confirmar SHA real y revisar los registros existentes de sincronización: llamadas, errores, fechas saturadas, particiones, asociaciones y enlaces pendientes de derechos. Comprobar en partidos reales qué datos llegan a la ficha y qué contenido puede publicarse. No cambiar una clave, comprar un plan ni desactivar protecciones para obtener indicadores verdes.

## Documentación oficial consultada

- https://www.thesportsdb.com/documentation : filtro `l` y límite Premium 50 para `eventshighlights.php`, V1/V2 y fechas de consulta.
- https://www.thesportsdb.com/api.php : capacidades Premium. Su tarifa pública no sustituye la factura del usuario.
