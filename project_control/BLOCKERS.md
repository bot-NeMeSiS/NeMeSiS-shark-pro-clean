# Blockers

Actualizado 2026-09-19. Condiciones transversales enlazadas desde la cola, no otra lista de tareas.

<!-- blockers:start -->
| ID | Motivo | Desbloqueo |
|---|---|---|
| ART | H07/anatomia/fondo y conformidad global no aprobados; R9 sin evidencia | Comparacion concreta con las 16 referencias y decision artistica |
| EXTERNAL | Produccion, cobertura, cuota, derechos y feed no observados en esta fase | Permiso y muestra real fechada por SHA; nunca sustituir con fixture |
| PUBLISH | Candidato local sin autorizacion de staging ni publicacion | Revision del diff exacto y autorizacion posterior; despues CI y despliegue permitido |
| COMMERCIAL | Pruebas externas de renovacion/pagos no ejecutadas; ELITE+ sin contrato actual | Validar catalogo y recorridos autorizados sin cambiar precios ni cobros reales aqui |
| ENV | Doce positivos SE-01 y 43 ambientales historicos no recertificados | Reproducir en alcance necesario y reparar entorno sin desactivar seguridad |
| LEGACY | No estan demostrados todos los consumidores ni la prescindibilidad del contenido | Cero consumidores, alternativa, pruebas y rollback; UNKNOWN se conserva |
| MATERIAL | ZIP/parches anunciados no recibidos; especificacion V946 no recuperada | Aportar solo el material concreto si se necesita; no inferirlo por nombres |
<!-- blockers:end -->

/app: timeout productivo historico abierto. Mismo dataset local de 603 partidos:
A/B final sin perfilador 5.730/2.084/2.095 -> 5.737/2.085/2.040 s;
menos SQL, aislamiento preservado, sin mejora significativa de latencia.
No reproduce ni acredita la resolucion del incidente productivo. P50/P95 de
produccion INSUFFICIENT_SAMPLE. No ampliar timeout para ocultar el coste.
SHARK: precios observados sin vigencia/modelo validados permiten WAIT, no un pick.
Recuperacion de cuenta, Telegram y pagos externos no tienen entrega certificada aqui.
No se ha solicitado accion externa nueva ni se han suspendido automatizaciones.
