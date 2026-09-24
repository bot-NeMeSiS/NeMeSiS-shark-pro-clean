# V941 · Seguridad y modelo de acciones

## Frontera de ejecución
Las rutas nuevas verifican sesión Admin. Cada POST valida CSRF, estructura JSON exacta, tipos, campos, acción y parámetros. No existe resolución dinámica de funciones a partir de texto, ni shell, SQL arbitrario o acceso del modelo al filesystem. Las consultas no ejecutan las propuestas.

Las propuestas están ligadas al identificador autenticado, versión, caducidad y estado observado. La confirmación debe ser una petición separada con booleano explícito; el motor contempla frase reforzada para alto riesgo. El reintento real Telegram no tiene adaptador conectado y se rechaza desde V941.

La adquisición de ejecución se confirma antes del callback para impedir doble click concurrente. Repetir una propuesta finalizada devuelve su resultado, sin repetir efectos. Una interrupción en EXECUTING exige reconciliación manual; no se afirma entrega exactamente una vez a servicios externos.

## Configuración y auditoría
Se reutiliza automation_state con tres claves permitidas y tipos estrictos. Las únicas tablas nuevas almacenan propuestas y auditoría. Inicialización idempotente, sin migración destructiva ni cambio de DB_PATH. GET no crea el esquema del registro.

Cada ejecución registra actor, origen, versión, parámetros, antes/después, resultado y verificación. El historial rechaza UPDATE/DELETE. Rollback añade evento nuevo y exige que nadie haya cambiado la revisión. Los fallos del callback no guardan texto bruto de errores externos. Corrupción de un ajuste desactiva su presentación y muestra falta de evidencia. Bloqueo de lectura no activa defaults; timeout de lectura 0,2 segundos.

Esta cobertura corresponde al registro nuevo. Los gestores heredados conservan sus mecanismos; no se certifica una migración global de todas las mutaciones históricas a estas tablas.

## Frontera de IA y preview
No se envían prompts originales, usuarios, correos, sesiones, banners ni texto de proveedores al modelo. Solo tema/pregunta constantes y campos agregados permitidos. La clave se usa exclusivamente en el encabezado de transporte. Responses usa store=false, límite de salida, timeout, sin tools ni autoridad para confirmar. No se persisten conversaciones completas. La interfaz usa textContent para resultados.

Referencia de diseño de Responses: [guía oficial de generación de texto](https://developers.openai.com/api/docs/guides/text). La API real no se invocó durante QA.

El preview requiere Admin, no-store y CSP con scripts, conexiones y formularios bloqueados. Simula identidad únicamente en g durante esa petición; preserva la sesión y no actualiza usuarios. Todos sus enlaces permanecen en el preview y conservan plan/dispositivo; destinos sensibles quedan inertes.

## Evidencia ejecutada
98 pruebas puras de acciones/SHARK más pruebas HTTP incluidas en la regresión de 466 casos: acción desconocida, payload extra, tipo inválido, identidad ajena, expiración, carrera, repetición, rollback obsoleto, secretos canario, respuestas malformadas, OpenAI ausente/error, inyección de contenido y contexto seguro. También se verificó la creación real de incidencia en almacenamiento local desechable y el retorno del prompt, sin duplicar al repetir confirmación.

Los tests emplean SIMULATED_QA y callbacks controlados. No representan una auditoría exhaustiva del repositorio entero ni certifican servicios externos o producción.
