# V874 SHARK Safe Mode and Value QA

## Estado

Render real indica `openai_configured=false`.

## Criterio V874

Cuando OpenAI no está configurado:

- Mostrar `Modo seguro activo`.
- Mostrar `Análisis limitado sin proveedor IA`.
- No prometer IA avanzada real.
- Mantener fallback interno con datos reales disponibles.
- No exponer claves ni nombres de variables al cliente.

## Resultado

V873 ya introdujo estados seguros; V874 los preserva y los valida en runtime/check.

