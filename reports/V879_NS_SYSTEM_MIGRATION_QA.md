# V879 NS System Migration QA

## Sistema visual canónico

V878 consolidó la UI alrededor de clases `ns-*`. V879 verifica y preserva esa dirección sin añadir una nueva capa visual.

## Confirmado

- `static/app.css` contiene el bloque `V878 UI LAYER PURGE LEGACY CLEANUP SINGLE SYSTEM`.
- `templates/partials/ui_components.html` emite clases `ns-*` en macros principales.
- Las macros `reference_*` quedan como puente compatible y deprecated.
- Sentinel conserva reglas V878 para detectar uso legacy, CTAs duplicados, navegación cruzada cliente/admin y claims falsos de Stripe/OpenAI/Telegram.

## Riesgo controlado

La retirada física de estilos antiguos queda aplazada hasta tener capturas reales. V879 reduce riesgo operacional y prepara un deploy verificable.

## Criterio para borrar legacy

Solo se debe borrar legacy si:

- Render sirve V879.
- Browser QA real está ejecutado.
- Sentinel sigue en 10.0 o sin issues reales.
- No hay pantallas con regresión visual.
- No hay macros `reference_*` llamadas por templates primarios.
