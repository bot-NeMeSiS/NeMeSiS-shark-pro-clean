# V871 Macro Dedup Fix

## Revisado
- `templates/partials/ui_components.html`.
- Botones de acción.
- Cards de picks.
- Cards admin.
- Estados seguros.

## Corregido
- Mojibake en `Pick en revisión`, `Requiere sincronización real`, `Acción pendiente` y `Revisión segura`.
- Botón SHARK con texto visible claro: `Abrir SHARK`.
- `aria-label` queda para accesibilidad, no como texto duplicado visible.

## Resultado
Las macros son más seguras para cliente, admin y Sentinel sin cambiar datos reales.
