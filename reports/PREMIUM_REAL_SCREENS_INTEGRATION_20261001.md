# Integración Premium y pantallas reales

Solicitud del usuario (2026-10-01): llevar las mejoras TheSportsDB Premium y lectores de highlights a las pantallas y permitir su uso real, no limitarse a preparar PRs.

## Integración comprobada antes del despliegue

Se combinan los cambios de #137 y #138, preservando los contratos de identidad, derechos, lectura y presupuesto. La fuente combinada fue publicada en `5f328527813e7286a6884ff148ef63248724d9c6`. Esta entrega registra #138 como segundo padre porque su código y su workflow de QA se incorporan íntegramente; no se modifica esa rama ni otras PR.

El Smoke de las ramas separadas no estaba aprobado: #137 tenía 13 fallos de ajustes ilegibles y #138 un caso positivo de proveedor simulado sin clave configurada. Se aplica la corrección de settings con hashes de código antes/después ya revisados, conservando la API values-only para otros consumidores; el caso positivo configura explícitamente una clave sintética, sin retirar el guard de clave ausente ni cambiar sus aserciones de LIVE/identidad.

Run `36889646921`, artifact `11176126561`, SHA256 ZIP `db6671f70ea8d608eacd6ef796b8f3295a41aa5c7ff1fed5ef6e114e8bd8fa7e`: **379 pruebas ejecutadas, cero fallos/errores/omitidos**, XML descargado y comprobado. Compilación, Jinja y Madrid Time correctos. Incluye 26 casos de ajustes reales, 39 HTTP frío y 41 de eficiencia Premium, más regresiones deportivas, identidad, revisión y Cron.

Hash SHA256 app.py combinado: `cff12d12bea16b7b93f2f6a3e37afed66e0539ba4448a7902b1beedaf9f97a5f`. Los hashes de los otros motores están en el artifact. El primer ensayo pasó los mismos 379 casos pero no publicó porque el token Actions no tiene permiso workflows. No se amplían permisos: Actions publicó solo fuente; los workflows permanentes se actualizan con el conector autorizado. El preparador temporal se retira. QA permanente es contents:read y conserva todos los controles existentes.

La suite completa y navegador del HEAD final deben comprobarse antes del merge. Esta evidencia de integración aislada NO certifica producción ni uso de la cuenta Premium real.

## Activación operativa sin eludir controles

El lector del detalle de partido ya consume `attach_detail` y `cached_statistics`; calendario y centro de resúmenes leen el catálogo común. Los datos guardados no requieren una consulta externa por cada usuario. Los vídeos mantienen revisión de derechos y reproductor opt-in; no se autoriza automáticamente material externo.

El control existente de los dos trabajadores es administrativo y con CSRF, persistido en SQLite, no una variable de entorno: `/admin/highlights-review#postmatch-workers`. Seleccionar TheSportsDB, activar ambos trabajadores y confirmar condiciones permite guardar un presupuesto de recuperación (por defecto 60 consultas adicionales/día compartidas). El botón Ejecutar un lote pendiente permite comprobar la primera entrega. `/api/admin/postmatch/status` conserva estado, errores y uso para la sesión autorizada. El Cron maestro existente ya llama al tick; no crear otro Cron.

No se inventa sesión administrativa ni se activa mediante un nuevo endpoint/bypass. El workspace Render debe estar confirmado por el usuario antes de usar sus herramientas de administración. La integración de código no cambia automáticamente una pausa administrativa.

## Validación en producción pendiente al escribir este informe

Tras controles del HEAD, merge autorizado en main y verificación del Auto-Deploy existente: comparar SHA real, abrir resultados, un partido final real y el centro de resúmenes; comprobar datos con fuente y fecha. Leer diagnóstico con sesión autorizada, activar lote solo con TheSportsDB ya contratado y confirmar filas recuperadas en ese mismo partido. Diferenciar datos ausentes, revisión de vídeo y fallo de lectura. No prometer todos los vídeos ni perfección a partir de pruebas sintéticas.

No se cambian usuarios, membresías, Stripe, pronósticos, envíos Telegram, claves o planes. No se borran ramas ni worktrees. La situación posterior de merge/despliegue se registra en la PR con evidencias reales.
