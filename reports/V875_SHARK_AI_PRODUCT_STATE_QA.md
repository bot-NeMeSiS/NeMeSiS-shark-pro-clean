# V875 SHARK IA Product State QA

## Runtime real

Render reporta `openai_configured=false`.

## Estado seguro esperado

- `Modo seguro activo`.
- `Analisis limitado sin proveedor IA`.
- No prometer IA avanzada real si falta proveedor.
- Mantener fallback util sin inventar datos.
- Admin debe ver una nota de configuracion futura sin exponer secretos.

## Decision V875

No se toca ninguna key. No se introduce proveedor nuevo. SHARK sigue operando en modo seguro hasta configuracion real.

