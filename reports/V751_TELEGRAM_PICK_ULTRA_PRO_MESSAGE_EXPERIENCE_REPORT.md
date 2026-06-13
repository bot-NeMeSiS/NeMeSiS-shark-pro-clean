# V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE

## Objetivo

Elevar los mensajes de picks enviados a Telegram a un formato ultra profesional, comercial y coherente con NeMeSiS SHARK PRO, sin tocar el cron V749B, sin cambiar secretos, sin modificar DB_PATH y sin inventar resultados, cuotas o métricas.

## Cambios principales

- Rediseñado `build_single_pick_message` para generar una ficha premium completa:
  - cabecera SHARK premium,
  - competición y hora Madrid,
  - partido,
  - entrada recomendada,
  - mercado,
  - cuota y casa,
  - stake en unidades y, si existe, importe,
  - score SHARK con barra visual,
  - edge/value si existe o etiqueta segura,
  - probabilidad SHARK solo si existe,
  - riesgo,
  - lectura SHARK,
  - motivos,
  - gestión y riesgos,
  - condición de entrada,
  - conclusión y aviso responsable.

- Rediseñado `build_daily_picks_message` para listados diarios con estructura profesional:
  - selección profesional del día,
  - máximo 3 señales top para evitar ruido,
  - orden por calidad existente,
  - mini ficha por pick,
  - hora Madrid,
  - stake, cuota, riesgo, edge y condición de entrada.

- Añadidos helpers internos en `engines/telegram_delivery_engine.py`:
  - `_bookmaker_text`,
  - `_quality_badge`,
  - `_confidence_bar`,
  - `_probability_text`,
  - `_ev_text`,
  - `_stake_money_text`,
  - `_odds_movement_text`,
  - `_pick_context_text`,
  - `_reasons_for_pick`,
  - `_risk_controls`,
  - `_entry_rule_text`,
  - `_premium_pick_card`.

## Reglas protegidas

- No se inventan cuotas.
- No se inventan probabilidades.
- No se inventa EV/edge.
- No se inventan resultados.
- Si falta cuota o selección clara, no se envía pick.
- La hora sigue pasando por `format_telegram_match_time_madrid`.
- El mensaje respeta HTML seguro para Telegram.
- Se mantiene límite de longitud Telegram.
- Se mantiene dedupe, cron y automatización V749/V749B.

## Archivos tocados

- `VERSION.txt`
- `engines/telegram_delivery_engine.py`
- `tools/check_v751_telegram_pick_ultra_pro.py`
- `tools/build_clean_release.py`
- `reports/V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE_REPORT.md`

## Validación esperada

- `python -m compileall app.py engines tools`
- `python tools/check_v751_telegram_pick_ultra_pro.py`
- checks heredados V749B/V749/V748/Madrid/security si están disponibles.

## Pendiente en producción

- Enviar un pick real o usar preview/dry-run desde `/admin/telegram/command-center` para comprobar visualmente el mensaje en el canal.
- Confirmar que los datos reales que llegan al pick incluyen los campos deseados: cuota, mercado, stake, motivo, riesgo y hora Madrid.

## Corrección adicional de horario en payloads Telegram

Se añadió `_localize_pick_for_telegram()` para conservar campos horarios originales cuando una normalización previa recibe payloads no estándar y puede truncar `kickoff_time`. Esto evita que Telegram muestre valores tipo `2026- · Madrid` cuando el dato original era un ISO válido como `2026-06-13T20:00:00Z`.

El formato final esperado para Telegram es:

`Hoy · 22:00 · Madrid`

si el ISO UTC corresponde a esa hora en Europe/Madrid.
