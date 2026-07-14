# V937 Diamond Project Cleanup

## DELETE_SAFE ejecutado

- `debug.log` local eliminado.
- Cinco DB temporales Diamond y sus artefactos de prueba eliminados.
- Matrices Browser QA añadidas a `.gitignore`.

## EXCLUDE_FROM_RELEASE

- PNG/JPG/WebP de `reports/`.
- `release_output`, `tmp`, caches, logs, ZIP internos, DB, WAL/SHM, backups y secretos.

## Preservado

Runtime, migraciones, tests, herramientas, referencias, service worker, manifest, legales, rollback y compatibilidad histórica.

No se ejecutó una purga masiva. Los CSS, componentes y macros antiguos sin prueba suficiente quedan en `MANUAL_REVIEW` o `ACTIVE_COMPATIBILITY`.
