# V888 Copy Text Errors Sweep

## Correcciones V888

- Login cliente: acentos y copy de membresías saneados.
- Registro: acentos y copy de membresías saneados.
- Base shell: se preservan textos saneados de V887.
- Calendario: labels `Mañana`, `Próximos`, `España`, `Andalucía`.
- Admin Go-Live: sustituido texto mojibake y claims falsos por estados honestos.

## Reglas

No debe aparecer visible:

- mojibake;
- `None`;
- `null`;
- `undefined`;
- copy técnico al cliente;
- claims falsos de Stripe, OpenAI, Telegram o datos deportivos.

