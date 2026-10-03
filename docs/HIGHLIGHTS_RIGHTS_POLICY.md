# Política central de highlights

La asociación al partido no concede derechos de publicación. El motor activo
`engines/sportsdb_highlights_engine.py` conserva la asociación por identidad
SportsDB inequívoca y el fallback estricto de fecha, equipos y competición.
No se modifica una asociación dudosa ni se autoriza masivamente el catálogo.

`engines/highlight_policy_engine.py` registra políticas con fuente, canal APP,
modalidad EMBED/LINK_ONLY/BLOCKED, evidencia documental, URL, fundamento y
alcance, atribución, uso comercial, fecha de verificación, revisión/expiración,
revisor y revocación. La revisión individual existente es el adaptador de alta:
registra por defecto una política limitada a la URL exacta, con revisión en
180 días salvo fecha expresa. La política se evalúa al leer el catálogo;
vencimiento y revocación no necesitan un botón de actualización ni más Cron.

La reutilización para futuros vídeos exige identificar el canal estable en
metadatos del proveedor y verificar expresamente que la evidencia cubre ese
alcance. No se infiere un canal por título, equipos, dominio YouTube o una
suscripción Premium. La regla es prospectiva: solo cubre registros recibidos
después de documentarla, no los 135 highlights previamente asociados. Cuando
falta ese identificador, el formulario solo permite política del vídeo concreto.
Una revisión individual pendiente o un bloqueo prevalecen sobre una regla de
canal; conflictos, expiración, revocación, canal no cubierto y falta de asociación
vuelven a REVIEW_REQUIRED. Se conserva el catálogo y su evidencia, sin borrado.

El panel de revisión muestra políticas y permite revocarlas mediante POST
protegido por sesión Admin y CSRF. Las consultas son de solo lectura y nunca
crean schema. El alta explícita usa la misma transacción de revisión del vídeo.
Los adaptadores de decisiones anteriores se conservan: no se reescriben sus
licencias ni se autorizan registros desconocidos por una migración.

Los consumidores del catálogo y Match Center pasan por el mismo clasificador.
LINK_ONLY nunca carga un iframe. EMBED utiliza el reproductor compatible
existente y YouTube-nocookie cuando corresponde; requiere activación del usuario,
sin descarga, rehosting o autoplay obligatorio. Las miniaturas tienen una
decisión de derechos separada. Un permiso documental no certifica que el
reproductor externo esté disponible en todas las regiones.

Excepciones observadas en Admin LIVE el 3 de octubre de 2026:

| ID local | Título | Enlace original | Observación |
| --- | --- | --- | --- |
| 957d518a403a4369f14579 | New Mexico United vs Sacramento Republic | https://www.youtube.com/watch?v=rJtKqOVJ1PU | Sin fecha mostrada y sin asociación inequívoca |
| 3ab6fffd41bf8a985646ad | FC Tulsa vs New Mexico United | https://www.youtube.com/watch?v=L5wtOa6bvlc | Sin fecha mostrada y sin asociación inequívoca |

La lectura muestra 137 guardados, 135 asociados y dos sin asociar. No se fuerza
su match_id, fecha o competición a partir del título. No se registra ninguna
licencia real ni se aprueba ningún vídeo durante esta implementación.
