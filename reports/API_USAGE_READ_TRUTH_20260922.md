# Control de consumo y caché: lecturas seguras y estados verificables

22/09/2026. Ampliación de PR64 sobre su HEAD 75ba71e3496a4fd868183975cfb66bdf5dc3f61b, ya reconciliado con main PR66 666f0580c7d036606921d08e368be8d14888ab93. Este informe describe un candidato, no una publicación.

## Defectos corregidos

1. El resumen de consumo ocultaba un fallo de lectura y devolvía cero consumido/todo el presupuesto restante. Ahora diferencia READY, NOT_INITIALIZED y READ_UNAVAILABLE. Cantidades desconocidas se devuelven como null y en administración como «No verificable»; un registro válido realmente vacío sigue siendo cero. Si falla la lectura de un proveedor, no se publican balances parciales como si todo fuera verificable.
2. Consultar el presupuesto o la caché inicializaba tablas y podía crear una base vacía si la ruta era errónea. Ambas funciones abren solo un archivo existente con mode=ro, query_only y una transacción de lectura. No migran, crean ni modifican registros. Sus conexiones se cierran también ante errores. Esta garantía corresponde a estas funciones, NO a todos los GET o paneles heredados de la app.
3. Lectura y reserva emplean la misma suma validada. Una fila ALLOWED con un importe no entero o nulo ya no se trunca o interpreta como cero para conceder más permiso. Se deniega sin reparar o borrar datos silenciosamente. Las reservas negativas enteras históricas siguen ignoradas, nunca generan crédito.
4. La caché calculaba el vencimiento por hora local: un TTL de 120 segundos podía prolongarse una hora durante el retraso de reloj de Madrid. Ahora se calcula por tiempo transcurrido en UTC. La caché sin fecha, con fecha inválida o vencida no se devuelve como actual. El mínimo y los TTL configurados permanecen intactos.
5. El panel de automatización identifica los dos contadores como reservas locales, no saldo real contratado. Una lectura no verificable no muestra el indicador general como OK en ese panel. Las protecciones de acceso se conservan.

## Alcance y continuidad

Solo se modifica el módulo del guard y su presentación administrativa; se añade un archivo de pruebas y este informe. Se conserva el resto de PR64: reservas atómicas, transacciones cortas, simulación sin consumir la reserva diaria y reconciliación deportiva sin sobrescribir estado/marcadores/relojes del proveedor. No se habilita gthread ni se cambia el runner real de cinco minutos.

No se ha consultado una API, cambiado una clave, borrado caché productiva, gastado crédito, creado cuentas reales, enviado Telegram, cobrado o apostado para estas pruebas. La estimación solo cubre reservas registradas por este guard, no todas las llamadas de todos los motores. Que el lector devuelva desconocido no concede permiso: la autorización vuelve a comprobar y reservar en la base, independientemente del resumen de pantalla.

Esta reparación no resuelve el error de acceso de API-Football observado anteriormente, no activa el archivo de estadísticas ni publica los vídeos. El candidato local de archivo se ha conservado aparte y sus 69 regresiones se repitieron correctamente, sin incorporarlo a esta rama. No se reenvía el lector de Match Center bloqueado en una intervención anterior. Las estadísticas completas necesitan su propio cierre de recepción, conservación y presentación.

## Pruebas y límites

Pase local final: 226 casos distintos aprobados, cero fallos/errores/omisiones; 32 son nuevos. Incluye regresiones anteriores de transacciones, presupuesto, estados deportivos, sesiones, constructor, revisión de borradores y caché decorativa. No es toda la suite del repositorio ni una medida de rendimiento productivo.

El primer pase de 22 casos nuevos produjo 16 fallos y 6 éxitos contra la versión anterior de la rama; se conserva su XML. Una prueba adicional asumía que 3000 niveles JSON provocarían RecursionError: falló porque la app puede elevar el límite de recursión. Se sustituyó esa suposición por una inyección explícita del error del decodificador, sin modificar lógica heredada, criterios o workflows. Ambos resultados intermedios se conservan; no se suman los pases repetidos.

Nuevos casos: archivo ausente, directorio/corrupción/bloqueo exclusivo, esquema ausente, cero legítimo, lectura parcial fallida, SQL sin mutaciones, cierre de conexiones, escritor reservado simultáneo, fecha de caché ausente/errónea/caducada, TTL durante cambio horario, filas de presupuesto ambiguas, respeto de entorno explícito y pruebas reales Flask de administración/API con estado desconocido y acceso protegido. Datos y DB temporales; sockets externos bloqueados en los casos nuevos.

Compilación, 208 plantillas Jinja, comprobaciones v818 del guard/reconciliador y hora Madrid: aprobados. Escáner existente: 1224 archivos, cero hallazgos de secretos; dos avisos previos de privacidad en fixtures ajenos sin cambios. No hay pruebas visuales nuevas ni certificación de iPhone; se comprueba el HTML administrativo renderizado y los endpoints existentes.

La copia local procede de la distribución CI de PR63 con los cambios publicados de PR65/67/66 y la PR64 aplicada. Los archivos intervenidos se comparan con sus bases verificadas; el catálogo de 1072 textos conserva el blob oficial 9aa02a7dc2e43b211f590c930ea65588fb6a61e7. La copia local no sustituye ejecutar CI completo del árbol exacto de GitHub.

## Integración

Mantener la PR en borrador hasta QA, Preflight y Smoke completos del nuevo HEAD, revisión del contrato y cierre de la observación productiva actual. No reutilizar el aprobado del HEAD anterior ni interrumpir la certificación con un despliegue encadenado. No se cambian tests heredados, workflows o umbrales para aprobar. No aplicar el ZIP parcial sobre main ni /data. Registrar por separado el SHA integrado, los despliegues Web/Cron y el resultado posterior si llega a publicarse.

Referencia técnica consultada: documentación oficial Python sqlite3 (context managers cierran transacciones, no conexiones; modo URI ro), https://docs.python.org/3.11/library/sqlite3.html . Esta entrega no cambia versiones ni dependencias.
