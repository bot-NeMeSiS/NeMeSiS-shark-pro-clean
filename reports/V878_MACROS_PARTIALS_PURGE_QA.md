# V878 Macros Partials Purge QA

## Partial revisado

`templates/partials/ui_components.html`

## Cambios

- `status_chip` usa `ns-chip ns-badge`.
- `action_button` usa `ns-button`.
- `stat_card` usa `ns-card ns-stat`.
- `empty_state` usa `ns-empty`.
- `board_card` usa `ns-card ns-command-card`.
- `plan_badge` usa `ns-badge ns-plan-badge`.
- `match_row` usa `ns-card ns-match-row`.
- `pick_card` usa `ns-card ns-pick-card`.
- `sentinel_issue_card` usa `ns-card ns-sentinel-card`.

## Legacy

Las macros `reference_*` siguen disponibles por compatibilidad, pero ahora emiten `ns-*` y quedan marcadas como `v878-deprecated-visual-class`.

## Correccion de copy

Se corrigieron mojibakes en defaults de macros como `Pick en revision`, `Requiere sincronizacion real`, `Accion pendiente` y `Revision segura`.

