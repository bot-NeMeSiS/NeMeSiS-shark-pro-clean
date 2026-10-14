# Inicio por ligas: cambios y evidencia (2026-10-10)

## Estado

Implementación en la rama `fix/home-league-agenda-css-20261010`, sin merge a main ni despliegue. Base revisada: `bbc61473392b2511426ded728e34701ba2da2ef2`. Commit de implementación validado: `f9ecbe2f6de361fad8d271116c6643e04f5fe617`. Se conserva la identidad V941 del proyecto; no se afirma una nueva versión en producción.

Este commit de cierre solo elimina cinco archivos temporales utilizados para transferir/validar los cambios y añade este informe; no modifica la implementación validada.

## Cambios implementados

- La sección de partidos de hoy admite hasta 48 encuentros del snapshot disponible, frente a 12. Directos, próximos y resultados mantienen límites separados. No se inventan partidos ni se amplía el consumo de proveedores.
- Inicio público y de cliente utilizan la agenda agrupada. Cada liga tiene su propio bloque, cabecera, país, contador, acento visual y enlace. Los encuentros de una liga quedan juntos; un índice permite saltar entre bloques.
- Los grupos distinguen competición, país, temporada y deporte. Fechas y límites del día se evalúan en Europe/Madrid; se conservan estados canónicos, deduplicación y favoritos por usuario.
- Logos tomados de los datos del encuentro o perfiles de liga existentes. Consulta de caché en modo SQLite read-only, sin descargas ni escrituras durante el render. Nombres ambiguos no asignan automáticamente una liga de otro país. Cuando falta el logo o falla la imagen se muestra un distintivo alternativo, no un escudo oficial inventado.
- Se modifica el componente Home del sistema de diseño existente y se recompila product-system.css. En móvil los partidos son verticales y el índice de ligas ocupa una fila desplazable.
- Se sustituye la comprobación obsoleta de app.css por la validación del stylesheet activo product-system.css, versión, origen, unicidad, fingerprint de fuentes y hash del archivo servido. Se mantienen las comprobaciones de SHA, salud, datos y secretos de la certificación.

## Pruebas realizadas

GitHub Actions, ejecución `38056491954`, job `114225971559`: éxito. Artefacto `11671271518` (`home-league-review-38056491954`). SHA-256 del ZIP: `0fac5c84c5b9755129e01b7ab991e2c108332bc0347eead06794574a176269bd`.

JUnit: **115 passed, 0 failures, 0 errors, 0 skipped**. Compilación Python y build/check CSS correctos. La suite utiliza una base temporal inicializada y un guard que bloquea conexiones externas del servidor.

Las pruebas de navegador utilizan plantillas y CSS reales con datos SIMULATED_QA. Cubren inicio público y de cliente a 320, 390 y 1440 px, con JavaScript activado y desactivado; 30 partidos agrupados en seis ligas; navegación por teclado; ausencia de desbordamiento horizontal de página; logo disponible e imagen rota con alternativa. También pasan las pruebas existentes de Home, composición y aislamiento de contexto por solicitud.

Las capturas son de QA aislada, no de Render ni de partidos o logos oficiales reales. No equivalen a una certificación visual de producción.

## Detalle visual pendiente

La inspección posterior de la captura de escritorio detecta que una regla heredada puede reducir el tamaño del logo de liga respecto al tamaño previsto. Las 115 pruebas no incluyen una aserción de tamaño mínimo de ese logo. El intento posterior de aplicar ese ajuste y ampliar la prueba fue bloqueado por los controles de seguridad de la herramienta y NO se aplicó. No se afirma que este detalle esté corregido.

## Límites y publicación

No se ejecutaron envíos reales de Telegram, pagos, cambios de usuarios, escrituras en la base de producción ni nuevas consultas a proveedores deportivos. No se modifican Render YAML ni los workflows productivos en el diff final. El workflow temporal de esta revisión y sus cuatro archivos auxiliares se eliminan en este cierre.

Pendiente antes de publicar: resolver y verificar el tamaño del logo en escritorio; revisar los checks del PR; autorización de publicación; después, comprobar el SHA desplegado, logos/datos disponibles y certificación en Render. No hacer merge ni declarar producción corregida basándose solo en las pruebas aisladas.
