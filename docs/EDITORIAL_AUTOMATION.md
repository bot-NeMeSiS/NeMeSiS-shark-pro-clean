# SHARK Editor: noticias automáticas para la ficha

Extiende PR139 sin cambiar app.py, planes, pagos, Telegram, claves, programación
de Render ni otras ramas. No sustituye PR137 ni sus correcciones pendientes.

## Flujo
RSS2/Atom HTTPS aprobado -> metadatos -> asociación conservadora -> borrador o
publicación bajo política revisada -> ficha cliente. Nombres canónicos completos
de ambos equipos, competición revisada, final confirmado y noticia publicada
entre el inicio y 48 horas después. No hay matching difuso ni finales inferidos.
Ambigüedades y nombres no cubiertos quedan para revisión. Una asociación no prueba
las afirmaciones de la noticia. No se promete cobertura para todos los partidos.

El cliente recibe título descriptivo propio, medio, fecha y enlace. Los títulos
del feed son metadatos administrativos sujetos a la política aprobada; no se copian
cuerpos, extractos o fotografías. El resumen factual y el vídeo siguen utilizando
los datos y permisos existentes: no se genera texto con IA ni se descargan vídeos.

## Control y coste
En /admin/highlights-review/news se añade SHARK Editor: revisar pendientes, pausar,
fuentes, consumo y bandeja de excepciones. No es otro centro independiente.
Máximo cinco feeds no revocados, cada uno con evidencia, alcance de competición,
revisor, caducidad hasta 180 días y aprobación separada de autopublicación.
No viene ninguna fuente real aprobada. Registrar una fuente no activa el editor.

Activación explícita con presupuesto: 12 reservas/día por defecto, máximo 60,
compartidas entre fuentes; día Europe/Madrid. No representa toda la cuota de una
cuenta ni un coste monetario. Reserva previa, no reembolsada en fallos inciertos.
Un feed por tick; hasta 256 KiB, 50 entradas y 500 candidatos recientes. Si la
ventana es mayor no se afirma unicidad. Las agendas futuras no consumen esa muestra.
Revisión normal cada 2 horas, errores a 30 minutos, 2 y 12 horas. Revisión manual
no evita el mínimo de 5 minutos. Arrendamiento y versiones protegen concurrencia.

El POST /api/automation/postmatch/tick existente conserva los trabajadores de vídeo
y estadísticas y presta al editor el tiempo restante: hasta 8 segundos cooperativos
dentro de 20 del coordinador. DNS del sistema no es cancelable, no hay garantía de
límite absoluto. No se crea otro Cron, servicio, dependencia de producción, búsqueda
de pago ni llamada generativa. Abrir panel/ficha no busca en internet ni crea tablas.

## Revisión y recuperación
Pausar búsqueda conserva publicaciones permitidas. Revocar autorización o caducar
la política oculta las referencias automáticas sin borrar el historial, incluso
con Cron apagado. Renovar exige confirmación y no reactiva fuentes pausadas o
revocadas. Cambios de metadatos/identidad regresan a revisión sin sobrescribir
ediciones humanas ni republicar retiradas. Una fuente duplicada no puede apropiarse
del contenido de otra. Red fallida o feed vacío no borra lo válido ni prueba cero
cobertura. No se rastrean artículos para comprobar retirada o bloqueo geográfico;
el administrador conserva retirada manual. No se reescriben pronósticos previos.

## Seguridad y verificación
Admin + CSRF + revisión optimista + respuestas privadas. HTTPS, DNS público,
socket fijado al sockaddr validado y TLS con nombre original. Sin proxies,
redirecciones, cookies, credenciales o destinos internos. XML sin DTD/entidades.
La validación técnica no concede licencia. Red fuera de transacciones SQLite,
escrituras condicionadas a identidad, revisión de política y arrendamiento vigentes.

79 casos nuevos y 195 regresiones pospartido se prueban con datos aislados. El
workflow editorial conserva las 43 regresiones de la ficha y exige 12 casos HTTP
completos (FREE/PRO/ELITE/admin a 320/390/1440) desde tres referencias publicadas
por un feed sintético, no insertadas a mano. Chromium local bloquea localhost;
ese intento no se declara aprobado ni se sustituye por snapshots. CI valida HTTP.
Antes de producción: comprobar candidato y despliegue, conservar copia recuperable,
aprobar una fuente real con permiso/cobertura contrastados y ejecutar un lote acotado.
Las pruebas no conceden derechos reales ni certifican reproducción regional.
