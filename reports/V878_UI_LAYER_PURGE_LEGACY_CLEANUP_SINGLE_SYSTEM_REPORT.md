# V878 UI Layer Purge Legacy Cleanup Single System Report

## Objetivo

Reducir capas visuales mezcladas y establecer un solo sistema funcional sin borrar a ciegas.

## Cambios aplicados

- Versionado a `V878_UI_LAYER_PURGE_LEGACY_CLEANUP_SINGLE_SYSTEM_FINAL`.
- Runtime flag `has_v878_ui_layer_purge_single_system`.
- `base.html` activa `data-v878-shell`.
- `static/app.css` define el contrato canonico `ns-*`.
- `templates/partials/ui_components.html` emite `ns-*` en macros principales.
- Las macros reference quedan como deprecated bridge.
- Sentinel expone reglas V878 de purga visual.

## Probado local

Se ejecutan checks, Sentinel, Jinja, smoke y ZIP audit en la validacion final.

## No probado

No se hizo deploy ni browser QA real. No se declara Render V878 ni pixel-perfect.

