# V879 Final Sentinel Employee QA

## Objetivo

Sentinel debe actuar como empleado interno de QA, no como JSON crudo.

## Corrección V879

Reglas nuevas:

- CTAs duplicados.
- Huecos negros grandes.
- Cards gigantes.
- Endpoint técnico como contenido principal.
- Inglés técnico visible en cliente.
- `None/null/undefined`.
- Mojibake.
- Stripe/OpenAI/Telegram falsos.
- Más de dos acciones por card.
- Falta de estado seguro si no hay datos reales.

## Resultado esperado

Sentinel debe priorizar problemas visibles reales y mantener acciones peligrosas bajo aprobación.
