# V939 Telegram Intelligence QA

## Contrato probado

- La cola solo consume candidatos que pasan el pipeline.
- Dedupe usa partido, mercado, seleccion y membresia.
- Daily limit se aplica antes de crear previews.
- Cada mensaje contiene nota de juego responsable.
- El motor genera payload visual, no imagen ni envio.
- `send_executed=false`.
- `telegram_api_called=false`.
- Llamadas externas: 0.
- DB escrita: no.

Token, chat y entrega real no se prueban ni se afirman. Estado de produccion: `NOT_CERTIFIED`.
