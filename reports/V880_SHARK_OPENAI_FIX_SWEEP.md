# V880 SHARK OpenAI Fix Sweep

## Estado

Render real muestra `openai_configured=false`.

## Regla

SHARK debe comunicar:

- `Modo seguro activo`.
- `Análisis limitado sin proveedor IA`.
- No prometer IA avanzada real sin configuración.

## Corrección V880

Check V880 bloquea `OpenAI operativo` falso y preserva safe mode.
