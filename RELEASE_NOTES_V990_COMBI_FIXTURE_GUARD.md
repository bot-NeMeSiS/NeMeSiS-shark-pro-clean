# V990 — identidad de partidos y revisión de combinadas

Dos selecciones del mismo partido podían entrar juntas en una simulación cuando
sus proveedores usaban nombres distintos para un equipo. La revisión del servidor
ahora añade un veto por identidad compartida comprobada y conserva las cuotas,
identificadores y acciones de cada observación original.

- El catálogo agrupa después de los filtros y antes de paginar, usando referencias
  canónicas locales o la prueba nativa propia de un mismo proveedor. Una identidad
  desconocida o contradictoria conserva sus observaciones separadas.
- Preview, propuesta ELITE y revisión de borradores usan evidencia actual del
  servidor. Las marcas transitorias no proceden del cliente ni se guardan en las
  selecciones, su revisión o el borrador. El replay idempotente devuelve el ID
  antiguo; su revisión explícita sigue siendo necesaria para comprobar vigencia.
- Se conservan los límites de plan, vigencia, casa, cantidad y propiedad de cuotas.
  El producto continúa siendo una simulación: no coloca apuestas ni calcula una
  probabilidad conjunta calibrada. La ausencia de identidad compartida comprobada
  no demuestra independencia entre selecciones.
- La lectura de identidad usa un batch adicional acotado de partidos y como máximo
  un batch de 500 PK de competición, dentro de la transacción existente. No añade
  llamadas de proveedor, migraciones ni sincronizaciones.

La validación se registra por SHA en la evidencia de publicación. Los positivos de
alias del catálogo aportan ahora referencias sintéticas explícitas, conservando
sus aserciones de presentación y de cuota propia; los casos sin prueba siguen
separados. Esta versión no certifica cobertura completa de proveedores.

El coordinador compartido de Inicio, calendario, directos, métricas y polling es el
siguiente lote: se conserva su fallo reproducido de dos tarjetas frente a tres en
el contador. Backup, recuperación aislada y Fase 3 conservan sus gates pendientes.
