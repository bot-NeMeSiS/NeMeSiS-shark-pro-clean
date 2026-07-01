# V879 Deprecated Visual Class Usage Audit

## Alcance

Se revisó el uso de clases deprecated introducidas como puente de compatibilidad en V878.

## Hallazgos

- `v878-deprecated-visual-class` aparece en `templates/partials/ui_components.html`.
- No se detectó `v878-deprecated-visual-class` en templates principales de cliente/admin revisados de forma estática.
- Las macros `reference_*` siguen existiendo por compatibilidad y emiten también clases `ns-*`.
- Las macros canónicas ya emiten:
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

## Decisión

No se retira físicamente el puente legacy en V879. Retirarlo sin browser QA real podría romper pantallas secundarias o macros antiguas que todavía dependen del puente.

## Plan seguro V880

1. Desplegar V879.
2. Hacer browser QA PC/móvil.
3. Confirmar que ningún template primario depende de `reference_*`.
4. Migrar llamadas restantes a macros `ns_*`.
5. Retirar `v878-deprecated-visual-class`.
6. Eliminar CSS legacy solo si Sentinel y capturas reales quedan limpias.
