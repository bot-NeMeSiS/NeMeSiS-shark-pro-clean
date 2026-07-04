# QA seguimiento y resultados de picks

V889 prepara formato de seguimiento, pero no inventa liquidaciones.

Campos seguros:
- Resultado: ganado/perdido/nulo/pendiente solo si existe dato real.
- Marcador real solo si existe.
- Cuota original si existe.

Si falta cierre real:
- `Resultado pendiente`.
- `Marcador pendiente`.
