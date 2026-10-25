# V989 — Ventana de backup según la hora de Madrid

El Cron decide si corresponde intentar el backup entre las 04:30 y las 06:30
de Europe/Madrid durante todo el año. Antes fijaba 02:30–04:30 UTC: tras el
cambio de hora del 25 de octubre eso adelantaba una hora la ventana local.
La nueva condición conserva el límite inicial inclusivo y final exclusivo.

Las etiquetas del Centro de Mando y la documentación describen la misma
ventana. No cambia la cadencia de cinco minutos, la duración local de dos
horas, los plazos, presupuestos, recursos, deduplicación ni bloqueos. Tampoco
se alteran capacidad, integrity_check, hash, manifiesto o publicación atómica.

Validación local previa: el problema se reprodujo con cuatro fallos de borde
en invierno. Las 94 pruebas puras corregidas pasan, incluyendo verano,
invierno, transiciones, entradas aware/naive y los cuatro asserts originales
de septiembre. Un barrido comprueba cuatro bordes por día de 2026. Las
pruebas se ejecutan aisladas y no invocan tareas ni el reloj de producción.
La integración y publicación requieren además los controles de release.

El bloqueo observado STORAGE_CAPACITY sigue pendiente. Corregir el horario
no acredita que exista una copia: backup real, integridad, hash, manifiesto,
restore aislado y Fase 3 siguen requiriendo sus propias evidencias.

No se ejecuta un backup manual ni se cambia el disco de 2 GB o el coste.
Las mejoras de identidad y conservación de observaciones de PR281 continúan
en revisión independiente; esta versión no las presenta como integradas.
