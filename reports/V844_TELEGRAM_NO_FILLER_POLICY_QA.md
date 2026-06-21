# V844 Telegram No Filler Policy QA

## Política
Si no hay candidatos top, Telegram no manda relleno al canal público.

## Estados internos añadidos/reforzados
- skipped_low_quality
- skipped_no_top_matches
- skipped_no_real_pick
- skipped_duplicate
- skipped_blocked_competition
- skipped_blocked_sport

## Comportamiento
- En admin se registra por qué no se envía.
- En canal público no se envían errores, logs, mensajes de vacío ni partidos flojos.
- Daily matches devuelve SKIPPED_NO_TOP_MATCHES si no hay top real.
- Daily picks devuelve vacío si no hay pick real enviable.
