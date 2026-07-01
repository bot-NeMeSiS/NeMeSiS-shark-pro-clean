# V883 Visual Rules Model

El Visual Company Worker detecta problemas visibles que no deben quedar ocultos por un Sentinel con score alto.

## Reglas visuales
- Botones repetidos.
- CTAs duplicados.
- Textos duplicados.
- Labels raros o tecnicos.
- Mojibake.
- `None`, `null` o `undefined` visibles.
- Cards gigantes o sin jerarquia.
- Huecos negros grandes.
- Empty states enormes.
- Tablas con demasiado aire.
- Overflow movil pendiente de browser QA.
- Bottom nav duplicada.
- Floating SHARK duplicado.
- Nav cliente dentro de admin.
- Nav admin dentro de cliente.
- Demasiadas acciones por card.
- Endpoint tecnico visible como contenido principal.
- Panel Sentinel pareciendo JSON crudo.
- Pantalla sin CTA principal.

## Criterio de score
Si una regla genera issue real, el score baja. V883 no permite score 10 cuando hay critical/high visibles.
