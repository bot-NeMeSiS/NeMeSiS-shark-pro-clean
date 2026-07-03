# V888 SHARK OpenAI Error Sweep

## Render real

`openai_configured=false`.

## Estado esperado

Cliente:

- Modo seguro activo.
- Análisis limitado sin proveedor IA.
- Sin prometer IA avanzada real.

Admin:

- Variable pendiente sin mostrar secretos.

## Corrección V888

Se corrigió el fallback JS de SHARK para que el GET alternativo use `/api/shark/ask?q=...`.

