# V878 Single UI System Report

## Sistema canonico

V878 define y usa:

- `ns-shell`
- `ns-card`
- `ns-card-compact`
- `ns-button`
- `ns-button-primary`
- `ns-button-secondary`
- `ns-button-ghost`
- `ns-chip`
- `ns-badge`
- `ns-stat`
- `ns-table`
- `ns-empty`
- `ns-match-row`
- `ns-pick-card`
- `ns-admin-card`
- `ns-command-card`
- `ns-plan-card`
- `ns-sentinel-card`
- `ns-mobile-section`

## Accion aplicada

- `templates/partials/ui_components.html` ahora emite clases `ns-*` en las macros principales.
- Las clases `v869-reference-*` quedan marcadas con `v878-deprecated-visual-class`.
- `static/app.css` contiene el bloque `V878 UI LAYER PURGE LEGACY CLEANUP SINGLE SYSTEM`.

## Decision

No se elimina legacy activo sin browser QA real. Se neutraliza mediante sistema unico y marcador deprecated.

