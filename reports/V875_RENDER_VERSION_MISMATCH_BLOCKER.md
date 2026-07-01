# V875 Render Version Mismatch Blocker

## Blocker principal

Render real sirve `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`, mientras local está preparando V875 sobre base V874.

## Impacto

- V874 no está certificado en producción.
- V875 no puede declararse desplegado.
- Capturas de producción no demostrarían V874/V875.
- El error `Invalid header value` sigue siendo de una versión vieja sin el saneado V873/V874.

## Acción requerida

Deploy manual de V875 y validación posterior de runtime.

