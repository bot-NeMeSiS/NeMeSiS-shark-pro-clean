# V879 Next Legacy Removal Steps

## Bloqueador actual

Render sigue sirviendo V855. No conviene borrar físicamente legacy hasta que producción sirva V879 y se hayan capturado pantallas reales.

## Orden recomendado

1. Subir contenido descomprimido del ZIP V879 a raíz GitHub.
2. Confirmar `VERSION.txt`, `APP_VERSION` y `app.py` en GitHub raíz.
3. Ejecutar `Clear build cache & deploy` en Render.
4. Confirmar `/api/runtime-version = V879_RENDER_DEPLOY_V878_BROWSER_QA_AND_LEGACY_REMOVAL_PLAN_FINAL`.
5. Ejecutar browser QA PC/móvil.
6. Auditar llamadas reales a macros `reference_*`.
7. Migrar llamadas restantes a macros canónicas `ns_*`.
8. Retirar `v878-deprecated-visual-class`.
9. Retirar CSS legacy no usado.
10. Crear V880 como retirada física segura, no como rediseño nuevo.

## No hacer todavía

- No borrar CSS legacy en bloque.
- No retirar macros `reference_*` sin búsqueda y browser QA.
- No declarar pixel-perfect sin capturas.
- No avanzar otra capa visual antes de desplegar y revisar V879.
