# Recuperación pospartido: del dato a la pantalla

Base: main `047924de232e0e218f6d2477f89fa7fee0b30bce`. 01/10/2026.
El usuario activó los trabajadores y observó dos tareas RETRY (NO_VIDEO y NO_STATISTICS). Render confirma actividad automática, pero el log agregado anterior no identifica los eventos; no se atribuye una causa concreta a esas dos tareas sin evidencia.

## Defecto reproducido
El ejemplo oficial `https://www.thesportsdb.com/api/v1/json/123/eventshighlights.php?d=2024-07-07` devuelve `tvhighlights`. El colector activo no reconocía esa clave: trataba una lista válida como MALFORMED. Se añade a los dos lectores pertinentes. Reproducción aislada con el mismo objeto mínimo: antes FAILED/0 registros/1 llamada/MALFORMED; después OK/1 registro/1 llamada. Se conserva UNKNOWN_RIGHTS y la publicación bloqueada. La respuesta oficial consultada era una muestra pública histórica, no una consulta con la cuenta Premium de producción.

La proyección de highlights puede omitir equipos, fecha y estado. El nuevo fallback individual solicita una fecha UTC + liga verificada y asocia exclusivamente su URL al evento completo que ya superó identidad y final confirmado. Rechaza IDs/ligas incompatibles, datos contradictorios, múltiples URLs distintas y respuestas mal formadas; una respuesta de 50 filas sin coincidencia no prueba ausencia. Solo una consulta alternativa, bajo la misma clave, lease, presupuesto diario y plazo; no otro Cron ni un servicio de pago.

## Estadísticas y trazabilidad
El ejemplo oficial `https://www.thesportsdb.com/api/v1/json/123/lookupeventstats.php?id=1032723` confirma `eventstats/strStat/intHome/intAway`, que el lector ya reconoce. No se inventa un cambio de esquema para justificar NO_STATISTICS. Se separan lista realmente vacía, nombres no reconocidos, valores vacíos y estructura inválida. Se conservan ceros reales, identidades, alcance temporal y validación de consistencia.

Cada FINISH conserva evidencia cerrada en la auditoría existente: evento numérico, filas recibidas/reconocidas/aprovechables, ruta de búsqueda y clase de clave (pública de ejemplo o configurada sin certificar plan). Una respuesta correcta no certifica facturación, permisos ni suscripción. No se guardan claves/URLs/payloads en esa evidencia. El proceso web registra `event=postmatch_delivery`, permitiendo analizar un lote real con el conector Render sin pedir al usuario credenciales o repetir consultas. El cron agregado mantiene su contrato.

## Pantalla administrativa
El formulario manual usa POST→303→GET privado. El resultado tiene explicación en español, tareas, consultas, partido, motivo y siguiente revisión, con vuelta al panel. Recargar no vuelve a ejecutar la consulta. Las llamadas programáticas sin return_to_panel conservan JSON; admin, CSRF y no-store permanecen. No se exponen permisos nuevos ni se modifica app.py.

## Evidencia ejecutada al preparar esta entrega
Run36907679868, artifact11185121450, ZIP SHA256 d0975c9f98fe8deb1531d44e745963d954850fd8724b1d5d8d2a641e70ac8a63. XML descargado: **453 pruebas, 0 fallos/errores/omitidas** (34 nuevas de entrega, 40 de permisos y 379 regresiones). **195 plantillas** analizadas, compilación y Madrid correctos. Fuente producto: afe59f8af3a93e948e3f01c04b11502e7833fbc7. Los cinco archivos editados se verificaron con SHA256 antes/después; los hashes del artifact coinciden con la fuente local.

Prueba de integración: vídeo ausente en evento + proyección tvhighlights + estadística con cero legítimo → 3 consultas compartidas, enlace guardado pendiente de derechos y estadística recuperada en el lector del partido. No se extrapola el ahorro ni el contenido de esa muestra a producción. La suite general y las 9 comprobaciones visuales de la nueva pantalla deben comprobarse sobre el HEAD final; todavía no se declaran aprobadas en este informe.

Se retira el auxiliar temporal de transferencia y la exportación de fuentes. Workflow final contents:read, sin escrituras/push/deploy ni claves reales. No se alteran datos de usuarios, pagos, cuotas contratadas, Telegram, configuración de activación o autorizaciones históricas. No se modifica la PR editorial139: antes de fusionarla deberá reconciliar su composición del blueprint con este resultado manual.

## Verificación real pendiente
Una vez integrados todos los controles y confirmado el Auto-Deploy: leer logs WEB con postmatch_delivery en una ejecución natural. Verificar eventID, contadores, motivos y presupuesto. Un resultado vacío del proveedor no se transforma en valores inventados. La publicación de vídeos sigue pendiente de evidencia y revisión; no se garantiza contenido para todos los partidos. El defecto tvhighlights está probado, pero no explica automáticamente toda falta de estadísticas o vídeos en producción.
