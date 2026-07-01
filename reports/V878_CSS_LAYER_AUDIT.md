# V878 CSS Layer Audit

## Hallazgos

- `static/app.css` contiene muchas capas historicas V815-V874 con reglas `!important`.
- Hay familias visuales mezcladas: `.btn`, `.action-button`, `.v860-action-btn`, `.v864-action-button`, `.v868-pro-action-btn`, `.v869-reference-action-button`, `.v871-action-clean`.
- Hay varias familias de cards: `.card`, `.metric-card`, `.v860-stat-card`, `.v864-stat-card`, `.v868-pro-stat-card`, `.v869-reference-*`.
- Hay estilos admin/cliente coexistiendo en `base.html`; V878 mantiene aislamiento defensivo.

## Clasificacion

- Actual y usado: `ns-*`, `.card`, `.match-row`, `.pick-card`, `.status-chip`, `.admin-table`.
- Duplicado: familias `v860/v864/v868/v869` de botones, cards y chips.
- Legacy obsoleto: `v869-reference-*` como sistema primario.
- Peligroso: reglas antiguas con `!important`, no se borran sin capturas reales.
- Admin only: `.v808-admin-*`, `.v853-admin-command-strip`.
- Client only: `.bottom-nav`, `.v828-client-rail`, floating SHARK.
- Mobile only: reglas bajo `max-width`.

## Accion V878

Se crea un contrato canonico `ns-*` y las familias antiguas quedan como puente/deprecated. No se borran bloques historicos a ciegas porque pueden estar en templates activos.

