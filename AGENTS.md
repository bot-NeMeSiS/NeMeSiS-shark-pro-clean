# NeMeSiS: comunicación de cambios

Esta instrucción complementa las protecciones y guías existentes del proyecto;
no autoriza despliegues, fusiones, gastos ni acciones en producción.

## Regla del fundador (29 de octubre de 2026)

El fundador delega criterio para profesionalizar la plataforma, pero exige
conocer cada cambio y su motivo, especialmente los cambios visuales. No debe
encontrarse modificaciones por sorpresa ni tener que aprobar cada detalle.

- Antes de editar, comunica en español qué cambiará, dónde, por qué y qué se
  conserva. Agrupa cambios relacionados, sin ocultar cambios de alcance.
- Después, comunica qué se ha aplicado realmente y distingue local, rama/PR,
  CI, integrado y desplegado. Una PR no modifica la web publicada.
- Para cambios visuales actualiza `docs/VISUAL_CHANGELOG.md`, con antes/después,
  pantallas/roles, capturas o su ausencia, pruebas y reversión. No marques una
  composición como aprobada por tener imágenes previamente aprobadas.
- No conviertas este aviso en una solicitud de permiso para cada ajuste menor.
  Mantén las autorizaciones independientes ya exigidas para merge, deploy,
  pagos, cuotas, secretos, datos reales y acciones externas.
- No afirmes resultados de pruebas, ejecución de Codex o trabajo continuado que
  no estén acreditados. No ocultes limitaciones de una maqueta o prueba aislada.

Procedimiento: `docs/CHANGE_COMMUNICATION.md`.
