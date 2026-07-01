# V878 Buttons CTA Cleanup QA

## Hallazgo

Existian multiples familias de botones: `.btn`, `button`, `.action-button`, `.v860-action-btn`, `.v864-action-button`, `.v868-pro-action-btn`, `.v869-reference-action-button`, `.v871-action-clean`.

## Accion V878

- Todas las macros de botones principales emiten `ns-button`.
- Se definen variantes: `ns-button-primary`, `ns-button-secondary`, `ns-button-ghost`.
- V878 limita overflow visual de textos largos con `overflow-wrap:anywhere`.
- Las cards generadas por macros conservan maximo una accion principal y una secundaria.

## Pendiente

Quedan templates historicos que usan botones propios. No se reemplazan masivamente sin capturas reales para evitar romper rutas activas.

