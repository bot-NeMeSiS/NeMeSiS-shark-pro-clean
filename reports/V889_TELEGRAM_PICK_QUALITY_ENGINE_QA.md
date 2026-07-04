# QA motor de calidad de picks Telegram

Archivo: `engines/telegram_pick_quality_engine.py`.

Clasificaciones implementadas:
- `PREMIUM_SEND`
- `REVIEW_REQUIRED`
- `SKIP_LOW_QUALITY`
- `SKIP_MISSING_ODDS`
- `SKIP_MISSING_SELECTION`
- `SKIP_DUPLICATE`
- `SKIP_UNSUPPORTED_LEAGUE`
- `SKIP_TOO_LATE`
- `SKIP_TOO_EARLY`
- `SKIP_NO_REAL_DATA`

Regla clave:
- Sin cuota real, seleccion clara y partido real identificable, no hay envio premium.

El motor no escribe DB, no llama APIs y no envia Telegram.
