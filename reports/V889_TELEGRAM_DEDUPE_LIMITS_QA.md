# QA dedupe y limites Telegram

La dedupe key V889 incluye:
- Fecha Madrid.
- Tipo de mensaje.
- `match_id`.
- `pick_id`.
- Mercado.
- Seleccion.
- Cuota.
- Destino.
- Membresia.
- Modulo.

Objetivo:
- Evitar mismo pick repetido.
- Evitar misma combi duplicada.
- Evitar spam por partido.
- Preservar `QUEUE_SKIPPED` para saltos por limite.
