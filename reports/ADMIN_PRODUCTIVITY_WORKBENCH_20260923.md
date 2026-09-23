# Admin: jornada operativa y acciones verificables — 23/09/2026

## Base y alcance

Base main PR71: `706094630d337f9e329a8401fae217b316a9b49c`, árbol `63fb87401730ace4505b6d2b0102be86b1778972`. Candidato administrativo separado de PR60/vídeos y PR68/estadísticas. No cambia app.py, DB_PATH, proveedores, cron, pagos, usuarios, membresías ni Telegram. No despliegue en esta intervención.

Se reutilizan `/admin/operations-center` y sus cinco nombres de ruta existentes. No se crea otro panel, endpoint ni cola persistente. El dashboard añade «Jornada operativa» sin quitar sus accesos anteriores. El cambio de composición en blueprints/architecture.py añade dos líneas: conservar también el registro de media_review al integrar posteriormente PR60, no sobrescribirlo.

## Trabajo diario

Bandeja construida a partir del snapshot operativo ya existente, sin nuevas consultas, archivos o peticiones externas. Presenta primero hallazgos clasificados como confirmados, después investigación y evidencia pendiente, con prioridad dentro de cada grupo. Esa clasificación proviene del diagnóstico: no es una auditoría independiente ni certifica salud o frescura de proveedores.

Búsqueda por área, título, evidencia y siguiente paso; filtros de categoría/prioridad y directorio de doce herramientas existentes. Los enlaces se toman de una lista interna, no de URLs suministradas por un hallazgo. No se mezclan todos los tickets/colas de otras áreas: el directorio abre sus paneles, mientras la bandeja representa los incidentes de Operaciones.

Cada tarea permite consultar la evidencia y copiar un texto de investigación con su ID, contexto, panel, objetivo y criterio de cierre. Copiar no asigna trabajo, no ejecuta Codex, no marca revisado/resuelto y no activa trabajadores. Sin acceso al portapapeles se ofrece el texto para copiar manualmente; con JavaScript desactivado siguen disponibles tareas, textos y enlaces.

El diagnóstico detallado anterior queda desplegable, no eliminado. Las anclas abren el detalle que las contiene cuando JavaScript está disponible; sin él se conserva el desplegable nativo. No se cambia la fórmula heredada de puntuaciones ni se acredita que todas sus fuentes estén auditadas. La hora mostrada pertenece a la lectura local, no a una observación externa ni a vigilancia 24/7.

Una colección ausente/ilegible no aparece como cero en la nueva bandeja; una lista leída y vacía conserva cero. Filas malformadas y límites de 200 se declaran parciales. IDs repetidos se mantienen separados con aviso, sin fusionarlos automáticamente.

## Reparaciones de comportamiento

La plantilla anterior podía interpretar `section['items']` como el método del diccionario cuando faltaba esa clave; la reproducción HTTP encontró TypeError. Se utiliza get y se protege también el bloque de monitor independiente ausente. Las vistas parciales ya no rompen por esos dos accesos.

Las acciones originales conservaban nextIssue después de ejecutar un diagnóstico, aceptaban cualquier HTTP correcto sin verificar ok y permitían preparar otra acción simultánea. El nuevo controlador valida HTTP/JSON/ok y la identidad del prompt recibido. Un resultado de diagnóstico requiere renovar la bandeja antes de reutilizar acciones; no cambia silenciosamente la lista ni presenta una tarea distinta como la solicitada.

Bloqueo de doble acción en la misma pantalla, espera acotada a 20 segundos y ningún reintento automático. Si el resultado no se puede confirmar, se advierte que la operación podría haber llegado al servidor y se pide revisar antes de repetir. No es un bloqueo entre pestañas ni idempotencia nueva del backend. El backend previo y su auditoría permanecen sin cambios.

Se mantienen las guardas administrativas y los encabezados CSRF de la plataforma. Las respuestas de las páginas de Operaciones y sus APIs son private/no-store con Vary:Cookie. Los helpers solo se inyectan en esas páginas tras autorización. La presentación no se aplica a clientes.

## Pruebas de esta intervención

54 casos nuevos aprobados: 40 de lógica/plantillas/autorización y 14 de Chromium. Incluyen datos ausentes, límites, clasificación, duplicados, enlaces registrados, aislamiento de contexto, rutas administrativas reales con snapshots sintéticos, escape HTML, filtros, copia alternativa, sin JavaScript, respuesta fallida, prompt de otro ID, invalidación y exclusión de solicitudes simultáneas.

144 regresiones heredadas aprobadas de administración, lecturas, Combinadas y catálogo. Total local de dos grupos sin solapamiento: 198 aprobados. No es toda la suite del repositorio. Se recuperaron Flask/Werkzeug/Blinker/Stripe de wheels ya montados, sin descargar dependencias. Las pruebas HTTP conservan el route/render/autorización reales, pero inyectan datos sintéticos y no certifican el catálogo de producción.

Navegador: 320/390/430/1366 px sin desbordamiento en los componentes; no certificación de Safari/iPhone ni del shell completo. Capturas SIMULATED_QA. Transporte de acciones simulado, resto de red bloqueado. Los primeros intentos incompletos por límite de ejecución, el error de plantilla y fallos iniciales de búsqueda se conservan; se corrigió el producto. Dos bloqueos de helpers de navegador se arreglaron en las pruebas nuevas (CSS inline sin JS y función que configura fetch sin devolver una promesa pendiente). Al verificar los blobs se detectó una etiqueta option incorrecta: se corrigió y añadió la prueba del filtro confirmado; se repitió el grupo completo.

Auditor de navegación existente sin cambios: 831 rutas, 1150 entradas, cero rotas/cero botones sin acción; 274 advertencias conservadas. Compilación y sintaxis JS aprobadas; 211 plantillas parseadas y hora Madrid correcta. Escáner existente: 1246 archivos, cero secretos y tres avisos de privacidad conservados. La fuente local es la distribución del CI de PR71, no un clon completo; los tres archivos modificados de base se contrastaron mediante sus SHA nativos y los diez blobs de código/pruebas coinciden con los bytes probados.

## Publicación y pendientes

Exigir QA, Preflight y Smoke normales sobre el HEAD exacto antes de integrar. No forzar merge, alterar umbrales ni provocar otro deploy para documentación. No se han ejecutado acciones productivas, cobros, mensajes, consultas deportivas ni cambios de cuentas. Las capturas y la prueba del diagnóstico no acreditan una ejecución administrativa real en Render.

Quedan separados: revisión de todos los indicadores heredados, permisos reales de los futuros operadores, gestión/contestación de soporte y medición de tiempos con usuarios. Este bloque reduce dispersión y protege el uso del centro existente; no afirma automatización total, cierre de incidencias por sí solo ni operación continua certificada. Vídeos y estadísticas conservan sus pendientes propios.

## Continuación local: misión 1, shell completo (23/09/2026)

Este bloque conserva el cierre de la primera misión; la continuación Founder Control al final es el punto de reanudación vigente. Los recuentos anteriores describen otra intervención. Estado: **IMPLEMENTADO Y VALIDADO LOCALMENTE; NO SUBIDO, NO INTEGRADO, NO DESPLEGADO**.

- Rama reutilizada: `chatgpt/admin-operaciones-productividad-20260923`; HEAD `3ca19ad2a1df7dc26a2e50c89527a3630da95fda`, PR72 abierta/borrador comprobada. Base remota main `706094630d337f9e329a8401fae217b316a9b49c`.
- Worktree local aislado `nemesis-sentinel-operaciones`; ruta personal omitida de la copia compartida. Estaba limpio antes de seleccionar la rama preparada. Se conserva la rama Sentinel anterior; sin nuevo clon/worktree. Design no se ha editado. Main local continúa limpio en `454c3ca1abb79af6a8525f65daecc57c0958c0c1`; no se ha adelantado ni confundido con origin/main.
- Cambios propios: cinco archivos de producto (`app.py`, `engines/admin_operations_workbench.py`, `static/admin-operations.js`, las dos plantillas de Operaciones), dos archivos de pruebas existentes y esta continuación. No se cambia CSS, branding, datos reales, proveedores ni contratos deportivos. La afirmación histórica «backend sin cambios» no describe esta reparación: ahora se modifica únicamente el handler de generación del prompt.
- Huella SHA-256 del diff de código/pruebas antes de esta nota: `c5130edd66a199b888d074a088e208fb0d37f183664a0e23dee82d7070a91339`. Las huellas por archivo y del diff final están en `after/tree-check.json`.

### Tres defectos reproducidos y corregidos

1. **Identidad del encargo.** Un POST con `QA-NOT-PRESENT` devolvía HTTP 200 y la incidencia `QA-IDENTITY-1`. Ahora devuelve 404 sin prompt; ID conocido conserva su identidad, entradas mal tipadas devuelven 400, identidad duplicada 409 y colección no verificable 503. Se mantiene la compatibilidad documentada del consumidor antiguo que envía `{}` para pedir la primera tarea.
2. **Privacidad de texto copiable.** Credenciales sintéticas Bearer y asignaciones JSON escapaban al saneado. Se protegen esos formatos y Basic, claves API y access tokens; el prompt HTTP usa la misma normalización y una lista cerrada de campos. No se usaron secretos reales. Esto no equivale a auditar toda narrativa libre o todos los endpoints de la plataforma.
3. **Lectura desactualizada.** Tras guardar un diagnóstico se podía copiar la lista previa sin aviso en la propia bandeja; además el enlace de actualización solo cambiaba el hash de la página. Ahora se avisa junto a las tareas, se bloquea su copia mientras la lectura no esté renovada y ambos enlaces solicitan realmente un nuevo documento. Se conservan filtros y enlaces durante el estado pendiente. Un GET nuevo rehabilita la preparación de tareas. La incertidumbre no dispara reintentos ni cierra incidencias.

### Verificación de este árbol

- **221 PASS, 0 FAIL, 0 ERROR, 0 SKIP** en seis módulos: workbench, navegador de componente, contexto admin de solo lectura, integración Flask Combinadas, Madrid Time global y saludo. No es toda la suite ni CI remoto. No se trasladan los 198/31/322/874 históricos.
- **47 observaciones de shell Flask real**, sin incumplimientos de las expectativas comprobadas: login admin sintético, dashboard, Jornada, evidencia, copia alternativa, panel de Copias y recuperación y retorno; almacenamiento real del diagnóstico en directorio QA; actualización con GET nuevo; vacío frente a lectura no disponible; CSRF incorrecto, visitante y cliente rechazados; sesión caducada sin éxito ficticio.
- Doble clic: un POST. Timeout real de navegador a 20 segundos con operación sintética local de 21 segundos: resultado incierto, sin cancelación afirmada y sin reintento; el servidor termina después. No se ha añadido idempotencia entre pestañas a esta API histórica.
- Shell completo a 1366/390 y 320/430 px. Títulos largos, tres categorías y tamaño raíz de texto al 200% sin desbordamiento horizontal. Foco/teclado y fallback del portapapeles comprobados. Cero errores JS en el recorrido admin observado. No certificación exhaustiva WCAG, Safari/iPhone ni equivalencia pixel-perfect.
- Smoke cliente: `/app`, `/live`, `/combinadas`, `/shark`, `/support`: HTTP 200, contenido presente y workbench administrativo ausente. No certifica apuestas, entrega de mensajes ni datos deportivos productivos.
- Compilación en memoria, parseo de las plantillas cambiadas y diff-check: PASS. Escáner existente acotado al diff: cero secretos nuevos y cero avisos de privacidad nuevos; conserva un aviso heredado de privacidad en los archivos inspeccionados. No se cierra una auditoría global de privacidad.
- Aislamiento: SQLite aleatoria temporal, cuentas sintéticas, credenciales externas ausentes, jobs desactivados, red externa bloqueada en Python y navegador. Cero infracciones de la frontera en la ejecución final. Servidor QA cerrado al terminar; no se anuncia una preview persistente.
- Incidencias del arnés corregidas sin cambiar expectativas: selección explícita del Chromium QA ya instalado, log de pytest dentro del área temporal, UTF-8 de Python/respuesta HTML sintética y registro de todos los blueprints con la misma DB temporal. El 503 inicial de Combinadas provenía de dos rutas SQLite distintas en el arnés, no se reparó código de Combinadas ni se ocultó el fallo.

### Evidencia y referencias

Directorio de evidencia local: `pr72-admin-20260923`, fuera del repositorio; ruta personal omitida. No se adjuntan bases de datos, capturas privadas ni archivos de QA al candidato remoto.

- `before/result.json`: reproducción previa de los tres defectos; `before/shell-1366.png` y `before/shell-390.png`.
- `after/result.json`: observaciones reales de Flask/HTTP/browser sobre datos **SIMULATED_QA**, con huellas y rutas temporales. No observación de Render.
- `after/shell-1366.png`, `after/shell-390.png`: pantalla completa. `after/stale-full-shell-1366.png` y `after/stale-full-shell-390.png`: aviso, tarea anterior bloqueada y diagnóstico desplegado. Usar estas capturas completas, no la captura recortada del elemento que incluye un artefacto del header fijo.
- `after/large-text-*.png`: prueba de títulos largos y texto ampliado. `after/pytest.xml`, `after/test-guards.json`, `after/tree-check.json`: resultados técnicos del candidato local.
- Referencias abiertas: `reference_images/admin/reference_import_v900_01.png` (dashboard) y `reference_import_v900_07.png` (administración operativa). Son objetivos visuales, no vídeos de errores. No se recibió un vídeo pertinente reproducible en el alcance consultado: minuto/segundo **NO DISPONIBLE**. No se afirma haberlo visto.

## Continuación vigente: Founder Control, móvil y PC (23/09/2026)

Estado: **TRES DEFECTOS REPARADOS Y VALIDADOS LOCALMENTE; PENDIENTE DE INTEGRACIÓN Y PUBLICACIÓN AUTORIZADAS**. No se reinicia PR72 ni se sustituye Founder OS. Se conservan los ocho archivos locales de la misión anterior, sin staging. Mismo worktree, rama y HEAD `3ca19ad2a1df7dc26a2e50c89527a3630da95fda`. Main local continúa limpio; Design no se ha editado.

### Defectos y alcance propio

1. **La consulta escribía alertas.** Reproducido con SQLite temporal: GET Founder invocaba sincronización y resolvía un aviso generado al leerlo. Las rutas HTML/API usan ahora una lectura SQLite `mode=ro`, sin crear esquema, regenerar avisos ni cambiar reconocimientos, fechas o estados. Ausencia/error no se presenta como cero: HTML ofrece reintentar y API devuelve 503. La actualización explícita existente conserva generación, actualización, deduplicación y ACK; la ventana de repetición de avisos se prueba sin entrega externa. Un ACK explícito fallido ya no confirma éxito. Las escrituras normales de sesión/seguridad (por ejemplo el registro de CSRF rechazado) no son cambios de negocio.
2. **Bandeja sin recorrido operativo completo.** Founder ofrece Jornada y evidencia desplegable con estado, observación Madrid, referencia y siguiente acción. Los destinos proceden de un registro interno cerrado; el texto importado no decide URLs. Se reutilizan Jornada y sus paneles, sin copiar alertas a otra cola. Cabecera/sidebar permiten volver a Founder. Abrir evidencia y navegar no reconoce ni resuelve avisos. Se conserva búsqueda al volver desde el panel, y copiar una tarea sigue sin asignar un ejecutor.
3. **Identidad privada y controles móviles.** Operaciones cambiaba al manifest cliente; ahora las superficies administrativas enlazan el manifest Founder existente y las cliente conservan el suyo. La barra Founder existente estaba fijada al final del contenedor transformado (y >5900 px), no al viewport; se mueve fuera de ese contenedor, sin duplicarla. Se preservan enlaces y funciones. Cabecera, estado y acciones dejan de comprimirse en móvil. Respuestas administrativas son `private, no-store`; no se crea caché offline privada.

Diff propio de esta continuación: `app.py`, `engines/founder_os_engine.py`, `static/founder-os.css`, `templates/admin_founder_os.html`, `templates/base.html`, `templates/components/v933_navigation.html`, dos módulos de tests Founder y esta nota. Los otros seis archivos modificados de PR72 se conservan tal como estaban al iniciar Founder. Total acumulado: 15 rutas (14 tracked modificadas y un test nuevo), índice vacío. No cambia el icono, branding gráfico, contratos deportivos, cron ni trabajadores. El formato multilinea del CSS existente no añade otra hoja ni otra cascada.

### Evidencia online y límites

- Solo lecturas sin sesión: `/api/runtime-version` 200 informa `git_commit_hint=706094630d337f9e329a8401fae217b316a9b49c`; `/admin/founder-os` lleva a `/admin-login?next=/admin/founder-os`; API Founder sin autenticación devuelve 403.
- Manifest online: nombre `NeMeSiS Founder Control`, id/start `/admin/founder-os`, scope `/`, standalone. No se ha usado una sesión productiva ni probado acciones de negocio.
- Los cuerpos de ambas funciones manifest y service worker son idénticos a HEAD. Scope raíz heredado no ampliado; worker existente usa red para navegación, no añade almacenamiento de respuestas administrativas. No se certifica instalación, push, Safari físico ni comportamiento offline instalado. Que el manifest sea público no concede permisos administrativos.
- Móvil y PC online: está comprobada la entrada privada, no el recorrido interior autenticado. Falta recorrerlo con una sesión del propietario después de la integración autorizada. Ningún resultado local se atribuye a Render.
- LOCAL SAFE: cuentas sintéticas, SQLite temporal, credenciales externas ausentes, jobs desactivados, solo loopback. El acceso LAN existente usa token/expiración y se activa con su launcher; no se ha activado ni se ha abierto `0.0.0.0`, túnel o puerto externo. Esta misión no certifica acceso LAN desde un teléfono físico.
- Jornada consulta/clasifica evidencia, prepara textos y accede a módulos; un texto copiado no acredita solicitud, ejecución ni resultado. No se ha conectado un ejecutor remoto de desarrollo al PC ni se ha certificado vigilancia 24/7. Ese mecanismo permanece fuera del alcance.

### Validación final y capturas

- **254 PASS, 0 FAIL, 0 ERROR, 0 SKIP** en nueve módulos focales y de conservación; no suite global ni CI remoto. Incluye lectura y actualización explícita de alertas, ACK, deduplicación, ventana de repetición con entrega simulada exclusivamente en test, permisos, CSRF, IDs, privacidad de caché, PR72, Madrid y Combinadas.
- **43 observaciones del shell Flask/SQLite/browser real**, datos sintéticos: Founder → aviso → evidencia → panel, Founder → Jornada → tarea → panel → Founder; ratón, teclado y tap emulado, recarga/API sin cambios de negocio, filtros al volver, error de lectura/recuperación y sesión caducada. 1366/390 px y distribución/controles a 320/430; texto raíz al 200%. Cero overflow horizontal, errores JS o infracciones de red/escritura en el recorrido final. Smoke `/app`, `/live`, `/combinadas`, `/shark`, `/support`: HTTP 200.
- Compilación en memoria/Jinja/diff-check PASS. Secret Guard: cero hallazgos nuevos. Privacy: cero nuevos; un aviso heredado conservado. No se rebajan tests: se conserva literalmente el contrato `private, no-store` de PR72. El arnés se corrigió para seleccionar Chromium ya instalado y esperar la navegación antes de volver; no se instala software ni se ocultan errores como PASS.
- Evidencia bajo el directorio anterior, subcarpeta `founder`: `before/result.json` y capturas originales; `after/result.json`, `after/pytest.xml`, `after/test-guards.json`, `after/tree-check.json` con huellas por archivo. La huella final se recalcula después de esta nota. Capturas: `founder-viewport-1366.png`, `founder-viewport-390.png`, `inbox-viewport-1366.png`, `inbox-viewport-390.png`, `journey-viewport-1366.png`, `journey-viewport-390.png`, y `read-failure-430.png`. Son LOCAL_QA, no imágenes productivas ni prueba física de iPhone.
- Servidor QA detenido al terminar. Ruta probada: `/admin/founder-os`, dentro de la copia local autorizada. No se anuncia una URL temporal como preview aún activa.

### Punto de cierre local conservado

Ediciones funcionales congeladas. Revisar el diff acumulado de 15 rutas y las capturas, autorizar explícitamente integración/publicación si procede y ejecutar CI sobre el SHA que se autorice. Después, recorrido online con sesión autorizada y prueba física de Safari/PWA. Sin staging/commit/push/merge/deploy ni acciones productivas en esta misión. Las reparaciones anteriores de PR72 y los pendientes independientes de Directo, Design, PR60/PR68 permanecen preservados. No empezar otro frente automáticamente.

### Fase 1: preparación de PR72 (23/09/2026)

El propietario autoriza ahora un commit selectivo y push normal a la misma rama de PR72, conservándola como borrador. Las 15 huellas coinciden con el cierre local validado antes de sanear únicamente este informe; no cambia código ni pruebas y no se repiten los 254 casos. El CI exigido es QA, Preflight y Smoke del nuevo HEAD. La continuación vigente y sus resultados se registran en la issue #8, sin otra cola. Esta autorización no incluye merge, deploy ni acciones productivas. Un resultado local o CI verde no certifica el recorrido privado online, Safari/PWA instalada ni vigilancia continua.
