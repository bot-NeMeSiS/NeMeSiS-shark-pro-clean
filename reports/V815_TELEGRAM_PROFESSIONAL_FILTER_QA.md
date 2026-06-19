# V815 Telegram Professional Filter QA

## Resultado

Se mantiene la proteccion profesional heredada de V814.

## Certificado

- Telegram automatico no se ha reescrito.
- Canal profesional mantiene filtro de futbol.
- Se bloquean deportes no futbol, NBA, regionales menores, reservas, juveniles y amistosos flojos.
- Se permiten competiciones top como LaLiga y Champions.

## Validacion

`tools/check_v814_full_ecosystem_reconciliation.py` pasa en V815 y valida:

- bloquea NBA;
- bloquea regional;
- bloquea reservas;
- bloquea amistoso menor;
- permite LaLiga;
- permite Champions.

## No se ha tocado

- Cola Telegram.
- Cron endpoints.
- `TELEGRAM_BOT_TOKEN`.
- `TELEGRAM_CHAT_ID`.
- Deduplicacion.
- Segmentacion de membresias.
