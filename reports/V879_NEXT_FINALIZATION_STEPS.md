# V879 Next Finalization Steps

## Orden recomendado

1. Desplegar V879 correctamente en Render.
2. Confirmar `/api/runtime-version = V879_FINAL_PRODUCT_UI_UX_LAYOUT_FUNCTIONALITY_POLISH_FINAL`.
3. Ejecutar browser QA PC/móvil con capturas reales.
4. Validar admin autenticado.
5. Confirmar no scroll horizontal.
6. Auditar macros `reference_*` con uso real.
7. Preparar V880 para retirada física de legacy si las capturas son limpias.

## No hacer

- No crear más capas visuales.
- No borrar legacy sin browser QA.
- No afirmar Render final sin deploy.
- No inventar datos.
