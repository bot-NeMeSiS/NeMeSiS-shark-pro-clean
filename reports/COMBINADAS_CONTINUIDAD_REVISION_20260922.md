# Continuidad cliente: revisar borradores sin perder evidencia

Base remota comprobada: `cd4f26f9160d4309f1a2e659111065f2001451c4` (PR65), árbol `b2c1a7168aaef312420d71cb08bb4b3de1cb2768`. Esta entrega no integra PR59/60/64 ni el candidato local de estadísticas. No altera app.py, reglas de cuota, membresías, sincronizaciones, banco, pagos, Telegram o secretos.

## Cambio del recorrido

Mis borradores -> Revisar con datos actuales -> comparación por selección -> vista previa nueva -> guardar otra copia solo con confirmación explícita. El original se conserva sin UPDATE ni DELETE. No se acepta una selección distinta porque reutilice el mismo ID de pick. Cambios de partido, mercado, resultado elegido, casa o identidad del evento bloquean su reutilización automática.

La revisión usa la misma lectura de cuotas, estado y permisos del constructor; no consulta proveedores. Cada acceso verifica el propietario en SQL y los permisos actuales y guardados. La respuesta es privada/no-store y la lectura SQLite es query-only. Una cuota caducada aparece como histórica no utilizable, nunca rejuvenecida al abrir la revisión. Las ausencias no se rellenan con otros picks. El cálculo sigue siendo una simulación, no una apuesta ni probabilidad.

Nuevos accesos: GET `/combinadas?borrador=<id>` y GET `/api/client/combinadas/<draft_id>/review`. Las rutas antiguas siguen funcionando. Las acciones de guardado conservan el mismo POST/CSRF, revisión y clave de idempotencia de PR65. Releer un borrador no crea otra fila. Un precio cambiado entre la revisión y el guardado sigue provocando rechazo y nueva revisión.

## Defecto de formulario corregido

El constructor anterior volvía a imprimir un importe fijo y no restauraba las selecciones enviadas cuando rechazaba el formulario. Reproducción de las plantillas anterior y candidata con el mismo contexto: importe `19,37` y selección `p1` se pierden en la anterior y permanecen en la candidata. Esto es una reproducción de plantilla, no de una cuenta productiva.

La respuesta preserva importe, selecciones, número, perfil y fecha dentro de límites de tamaño. Una selección que deja de estar disponible se mantiene como casilla genérica marcada para que el usuario la retire expresamente. No expone información de picks ajenos o de otro plan. También conserva más de quince casillas visibles cuando el envío se rechaza por exceso, en vez de quitar silenciosamente las últimas. No se usa localStorage ni se añade JavaScript o precarga de proveedores.

## Validación local

224 pruebas de lógica y SQLite aprobadas, cero fallos/errores/omisiones, incluidas 30 nuevas. Selección: test_combi_draft_review, test_combi_advisor_contract, test_single_truth_projection y test_team_result_evidence. Nuevos casos cubren propietario, sesión ausente, cambio de acceso, corrupción del borrador, precios, estados, partido/selección reasignados, persistencia intacta, nuevas copias idempotentes y ausencia de esquema/base.

207 plantillas analizadas; compilación de los cuatro archivos Python intervenidos y check_madrid_times pasan. Escáner existente: 1218 archivos, cero hallazgos. Los dos originales locales coinciden con los hashes Git remotos leídos. La reconstrucción final del parche se verifica en el paquete.

Se añaden además 13 casos HTTP y de componentes, incluidos cinco escenarios Chromium (320/390/430/1366 px y sin JavaScript), pendientes de ejecución remota al preparar el commit. No están sumados entre los 224 aprobados. El entorno local no dispone de Flask, Werkzeug o Chromium; el intento normal de instalar dependencias falló por DNS. No se sustituyeron esas dependencias por imitaciones para declarar un aprobado. Se requiere el CI normal del repositorio completo, sin cambiar exclusiones, umbrales ni políticas.

La copia local usa la distribución CI de PR63 y los 17 archivos publicados por PR65, con hashes verificados de los dos originales intervenidos. No equivale a certificar todos los archivos opcionales de la app. Las pruebas sintéticas no son evidencia de cuotas reales o apuestas ejecutadas. El paquete de evidencia conserva logs/XML, reproducción de formulario y manifiesto.

## Publicación y pendientes

Mantener la rama como revisión hasta QA/Preflight/Smoke completos del HEAD. La observación productiva de PR65 `35695646033` figuraba en curso al inicio; no cancelarla con un merge. El estado final remoto se registra en el comentario de la PR para evitar un despliegue extra solo de documentación.

Las mejoras de estadísticas persistentes, acceso API-Football, vídeos y automatización conservan su estado anterior. Este cambio no añade modelos predictivos ni nuevos trabajadores externos. No corrige por sí solo la cobertura deportiva o las esperas del cron.

Referencias técnicas contrastadas: SQLite Transaction (`https://www.sqlite.org/lang_transaction.html`) y OWASP Authorization Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html`). La prueba del resultado es el código y su suite, no una afirmación de cumplimiento general.
