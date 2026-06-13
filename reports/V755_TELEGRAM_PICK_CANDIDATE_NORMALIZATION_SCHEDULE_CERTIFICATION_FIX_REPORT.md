# V755 Telegram Pick Candidate Normalization Schedule Certification Fix

## Objetivo

Cerrar el fallo real del flujo automático de picks Telegram donde el Cron funcionaba, pero `auto_picks` terminaba con candidatos a cero por descartes como `TOO_EARLY`, `OLD_MATCH`, `OUTSIDE_WINDOW`, `MISSING_ODDS` y `MISSING_MARKET`.

## Causa raíz

El flujo automático revisaba picks ya enriquecidos por la app, pero no existía una normalización central para candidatos Telegram. Algunos campos alternativos quedaban invisibles para el motor:

- mercado en `prediction`, `recommendation`, `title` o `content`;
- cuota en `best_odd`, `odd`, `price` o `cuota`;
- hora en `match_hour`, `kickoff_time`, `commence_time` o fecha/hora separadas;
- estado `telegram_test` convertido a borrador por la normalización de picks.

Además, un pick sin cuota real se descartaba por completo aunque tuviera mercado, selección y hora válidos. Eso impedía enviar avisos útiles cuando la cuota estaba pendiente.

## Corrección aplicada

- Añadido `normalize_telegram_pick_candidate(pick)`.
- Añadido `normalize_telegram_market_text(value)`.
- Añadido `normalize_telegram_odds(item)`.
- Añadido `normalize_match_time_madrid(pick)`.
- Añadidos campos auditables `_telegram_candidate`.
- `telegram_pick_sendability()` usa el normalizador central.
- `MISSING_ODDS` pasa a `MISSING_ODDS_WARNING` cuando el pick tiene mercado, selección y hora válidos.
- `Principal` y `Mercado principal` dejan de contar como mercado real para Telegram automático.
- `telegram_test` queda admitido como estado válido para candidatos controlados de admin.
- Se conserva dedupe por pick, partido, mercado, destino y día Madrid.
- Se mantiene canal global `TELEGRAM_CHAT_ID` como destino aunque no haya privados vinculados.

## Ventanas profesionales

El envío automático respeta:

- `TELEGRAM_PICK_WINDOW_HOURS_BEFORE`
- `TELEGRAM_PICK_MIN_MINUTES_BEFORE`
- `TELEGRAM_PICK_PRO_SLOTS`
- `TELEGRAM_PICK_URGENT_MINUTES_BEFORE`
- `TELEGRAM_SUMMARY_WINDOWS`

Los descartes por tiempo ahora explican si el pick está pasado, demasiado pronto, demasiado tarde o esperando slot profesional.

## Diagnóstico admin

El Command Center muestra candidatos V755 con:

- pick;
- partido;
- hora Madrid;
- mercado original y normalizado;
- cuota original y normalizada;
- score;
- razón de descarte;
- sugerencia de corrección;
- estado de dedupe;
- destino global o privado.

También se mantienen acciones controladas:

- Crear candidato Telegram de prueba.
- Ejecutar prueba automática controlada.

## Validación local

Prueba ejecutada sin enviar Telegram real:

`tools/check_v755_telegram_candidate_normalization_schedule.py`

Resultado:

- Cron sin secret: 403.
- Cron con secret: 200.
- Campos alternativos normalizados.
- Falta de cuota tratada como aviso no fatal.
- Falta de mercado real bloqueada.
- Partido futuro elegible.
- Partido antiguo descartado como `OLD_MATCH`.
- Partido demasiado futuro descartado como `TOO_EARLY` con siguiente ventana.
- Canal global usado como destino.
- Primer envío simulado: `SENT`.
- Segundo envío simulado: bloqueado por `DUPLICATE_ALREADY_SENT`.

## Estado

V755 deja el automático preparado para que Render Cron convierta picks válidos en mensajes Telegram sin intervención del admin, siempre que existan picks reales dentro de ventana profesional y con destino configurado.
