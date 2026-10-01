# Ficha editorial del partido

Base de desarrollo: main 1690df66. Alcance: ficha cliente y revisión de referencias
externas en el centro administrativo existente. No cambia app.py, identidades,
cuotas, membresías, pagos, Cron ni activación de los trabajadores pospartido.

## Implementado
- Resumen, vídeo y noticias por delante del análisis ampliado de SHARK.
- Resumen determinista del contexto canónico: marcador, estado y datos observados.
  Sin llamadas de IA ni afirmaciones de dominio deportivo inferidas de una cifra.
- Vídeo a petición del usuario mediante postmatch-media.js y sus decisiones de
  permisos existentes; una solicitud de iframe no prueba reproducción externa.
- Referencias de noticias revisadas, sin copiar artículos, imágenes ni fragmentos.
- Administración en /admin/highlights-review/news: elegir partido, guardar borrador,
  revisar evidencia, publicar y retirar conservando auditoría. POST con admin+CSRF.
- Asociación a la identidad persistida: un cambio de equipos/fecha/competición
  invalida la selección anterior. No se enlaza por parecido de nombres.
- GET de noticias en mode=ro; solo una acción válida inicializa las tablas nuevas.
- Sin imágenes remotas, trackers o reproductores cargados por las tarjetas de noticias.

## Límites que no deben ocultarse
La búsqueda automática de noticias en internet NO está implementada aquí. La
entrada de referencias es administrativa y exige evidencia del permiso y de la
asociación. No existe una nueva fuente aprobada ni una nueva suscripción. El
trabajador pospartido de #133 se reutiliza para vídeos/datos y no se reactiva.
La redacción factual se calcula desde el snapshot al mostrar la ficha, no es un
modelo generativo ni un nuevo trabajador editorial permanente. La automatización
editorial completa y los conectores de fuentes con licencia requieren otro cierre.

La PR137 de lectores de highlights es independiente y no se da por integrada por
esta entrega. No se reutiliza su estado de CI como validación de esta propuesta.

## Validación
`python -m pytest -o addopts='' -q tests/test_match_editorial.py`
`python tools/run_match_editorial_browser_qa.py --output /tmp/editorial-http`

El runner predeterminado usa HTTP real con la aplicación completa y JavaScript,
usuarios/partidos sintéticos y destinos externos bloqueados. Debe ejecutar los
12 casos FREE/PRO/ELITE/admin a 320/390/1440 px, sin fallos.
`--snapshot` solo es diagnóstico de CSS/controles nativos y NO sustituye HTTP.
El entorno local bloqueó localhost en Chromium; las capturas locales se etiquetan
como snapshots y no como QA de producción. No hay vídeos ni noticias reales en
las capturas de prueba. Producción, proveedores y reproducción regional pendientes.

Activación de fuentes/publicación de contenido real exige revisión propia.
No fusionar ni desplegar hasta comprobar el SHA final y los controles generales.
