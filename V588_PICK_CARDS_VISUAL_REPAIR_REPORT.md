# V588 — Reparación visual de cartas de picks

## Objetivo

Corregir las cartas de picks y recomendaciones que podían verse raras por conflictos de CSS acumulados entre versiones.

## Cambios realizados

- Aislada la página de picks con `picks-page`.
- Aislada la página de recomendaciones con `recommendations-page`.
- Añadidos estilos específicos para que las cartas de picks vuelvan a comportarse como tarjetas verticales.
- Corregido el conflicto de `.pick-card` que forzaba `display:flex` globalmente.
- Mejorada la presentación de métricas dentro de la carta.
- Mejorado responsive móvil para que cuota, confianza, riesgo y stake no se monten.
- Corregidos textos visibles: “Por qué entrar”, “Puntuación SHARK”, “Análisis SHARK pendiente de revisión”, “ningún pick es seguro”.

## Archivos modificados

- `templates/picks.html`
- `templates/recommendations.html`
- `static/app.css`

## Validación

- No se ha tocado lógica Python.
- No se ha tocado Telegram.
- No se ha tocado SHARK Learning.
- No se ha tocado membresías.
- Cambio centrado en UI/UX de cartas.
