# V879 Final Spanish Copy QA

## Reglas de copy

- Cliente en español natural, directo y comercial.
- Admin puede ser técnico, pero explicado.
- Sin mojibake visible.
- Sin `None/null/undefined` visible.
- Sin promesas falsas de datos, IA, pagos o Telegram.

## Corrección V879

El check V879 bloquea mojibake común, tokens técnicos visibles y frases peligrosas como `apuesta segura`, `garantizado`, `sin riesgo`, `Stripe operativo`, `OpenAI operativo` y `Telegram filler`.
