# V814 Telegram Pro Channel QA

## Estado

V814 conserva el filtro profesional de V813 y lo certifica con check nuevo.

## Bloqueado para canal automático

- NBA y deportes no fútbol.
- Juveniles.
- Reservas.
- Regionales.
- Amistosos menores.
- Ligas de bajo valor comercial.

## Permitido

- LaLiga.
- Premier League.
- Champions League.
- Europa League.
- Conference relevante.
- Serie A.
- Bundesliga.
- Ligue 1.
- Primeira Liga.
- Mundial.
- Eurocopa.
- competiciones UEFA/FIFA importantes.

## Validación automatizada

`tools/check_v814_full_ecosystem_reconciliation.py` comprueba bloqueo de NBA, regional, reservas y amistosos, y permite LaLiga/Champions.

## Nota

No se modificó el envío manual, la cola, dedupe, cron ni `TELEGRAM_CHAT_ID`.
