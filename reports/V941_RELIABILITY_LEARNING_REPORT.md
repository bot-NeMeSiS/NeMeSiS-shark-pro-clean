# V941: Fiabilidad integrada en PR92

Base certificada: ab60d75acf2f264c52acf7a970efa3f4b65d1f80. Misma rama integration/admin-master-control-v941, misma PR92 DRAFT. Sin merge/deploy ni cambios de Render, secretos, pagos o Telegram real.

## Causa y cambio
El ledger permitia RESOLVED sin comprobacion posterior; Improvement Workflow tambien admitia resolved libremente. Render/local comparaba solo version. El primer test de cierre se ejecuto contra la base y fallo: ok=True sin evidencia. Se conserva esa reproduccion local.

Ahora Sentinel exige causa, correccion, prueba de regresion, prevencion, deteccion y verificacion estructurada con SHA, fecha, alcance y referencia. Estados compatibles: FIXED_PENDING_VERIFICATION, VERIFIED, VERIFICATION_FAILED y RESOLVED. Un cambio de SHA, una recurrencia o una reapertura invalidan la comprobacion previa. El workflow y los consumidores de Company OS/outbox conservan estos estados. El cierre legado devuelve conflicto al faltar verificacion.

Registrar evidencia y resolver pasan por Action Registry, propuesta, confirmacion independiente, permisos, CSRF y auditoria de inicio/resultado. La evidencia aportada por Admin se rotula ADMIN_ATTESTED_EVIDENCE: el formulario no ejecuta tests ni comprueba externamente un informe; registrar PASS no certifica produccion.

## Memoria y prevencion
Se reutiliza sentinel_issues_memory, sin otra base de incidencias. Fingerprint SHA256 derivado de regla/superficie/ruta/componente/proveedor/job/error; no se confia en un hash entrante. Primera/ultima observacion, recurrencias, causa, correccion, tests, PR/SHA cuando existen y verificacion se conservan. La migracion no inventa fechas de memoria antigua. Secretos y tracebacks se eliminan del contenido retenido.
Escritura atomica con bloqueo y revision optimista: un escritor antiguo falla antes de borrar una recurrencia nueva. No se reintenta silenciosamente una accion de Admin.

Catalogo de aprendizaje integrado: cache no es disponibilidad actual; cuota desconocida no es cero; HTTP 200 no certifica deploy; version no es SHA; reparado no es verificado; consumidores deben comprobarse tras cambiar interfaces; sprint/check no es runtime desplegado.
STATIC_ROOT queda como incidente comunicado, sin inventar fecha ni commit. CI deriva el contrato de los consumidores actuales de telegram_visual_card_engine: quitar un simbolo aun usado falla; actualizar conjuntamente proveedor/consumidores permite un refactor valido. No es un detector universal de todas las interfaces dinamicas Python.

## Radar y UI
Fiabilidad es una seccion del Master Control, con radar compacto, identidad, incidencias, recurrencias, historial y aprendizaje. Reutiliza Sentinel, Workflow, Company OS y auditoria. SHARK responde localmente con CONFIRMADO, SIMILAR, POSIBLE RELACION o SIN EVIDENCIA; una palabra compartida no confirma un fallo. Para comparaciones estructuradas admite id=, ruta=, proveedor=, job=, error=, componente= y archivo=.

Radar determinista: fechas atrasadas de jobs/sync/proveedores/cache, recurrencias y regresiones, ausencia de tests criticos, identificadores de acciones de controles y evidencia de produccion. Cada senal conserva motivo, impacto y enlace. La navegacion estatica detecta controles sin contrato identificable; las pruebas de navegador verifican la ejecucion real de los controles modificados, no se afirma cobertura universal de todos los botones.
Advertencia temprana de cola con cuatro observaciones recientes y ordenadas y tres incrementos. Las observaciones se guardan solo durante un scan Sentinel explicitamente ejecutado, nunca al abrir Admin; son observaciones de scans, no ciclos Telegram inventados. Sin historial se muestra DESCONOCIDO.

Identidad distingue runtime, APP_VERSION, VERSION.txt, main SHA, candidata, desplegado y Render. Consume evidencia persistida de Company Sentinel; falta de SHA/fecha fresca permanece UNKNOWN. Una candidata distinta de main no se confunde con drift de produccion. Alineacion de identidad tampoco certifica por si sola toda la produccion.

## Verificacion
Pruebas de cierre sin evidencia, pruebas obsoletas/fallidas, recurrencia, colisiones obvias, escritura concurrente, privacidad, aprendizaje SHARK, consumidores internos y drift. Rutas Flask reales y Chromium PC/movil prueban formularios, confirmacion y ausencia de llamadas al abrir bajo LOCAL SAFE.
La primera tanda local (311 casos) paso; una tanda posterior detecto una expectativa incorrecta del nuevo test de auditoria: dos acciones externas producen cuatro entradas (inicio y resultado). Se corrigio la expectativa conservando ambas evidencias. No se cambia el motor de auditoria para hacer pasar el test.
CI del nuevo HEAD pendiente al escribir este informe. REPARADO != RESUELTO: el resultado final y links de ejecuciones del SHA publicado se registraran en la descripcion de PR92 y evidencia local, sin heredar verdes de ab60d75a.

## Limites pendientes para Release Candidate
Sin certificacion independiente del despliegue activo, servicios externos, pagos o Telegram. PWA instalada en Chrome/Edge/movil reales y certificacion integral final permanecen pendientes. Ningun estado de este bloque autoriza merge o deploy.

## Ultima verificacion local antes de publicar
171 casos distintos de las dos tandas finales aprobados, sin BOUNDARY_EVENTS. XML:
- data/local_dev/candidate-d411e187a3e44ab3bb6793ee0563a770/result.xml (167)
- data/local_dev/candidate-fc38df85cee1442f9133212247c1a852/result.xml (46; solapa con anterior)
Las rutas Admin completas tambien se comprobaron en la tanda candidate-e9a320eb3b364667a62d4b722e72e6d3; su unico fallo era la expectativa heredada de cierre sin evidencia del founder gate. Se cambio esa expectativa a pendiente y se revalido en la tanda final. No se omitio ni se debilito la regla nueva.
Navegacion estatica: 1186 enlaces, 0 rotos, 0 botones sin accion reconocible, 280 avisos. Scanner: 1284 archivos, 0 secretos y 3 avisos de privacidad heredados. JavaScript syntax PASS. Chromium PC/movil, formularios reales y controles sin envio automatico aprobados. Inspeccionada captura desktop del panel integrado; datos de QA sinteticos identificados.
