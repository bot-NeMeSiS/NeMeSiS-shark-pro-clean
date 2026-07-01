# V874 Sentinel Rules and Score QA

## Objetivo

Mantener Sentinel alto y útil tras cambios de copy/runtime/visual.

## Reglas revisadas

- Mojibake visible.
- `None/null/undefined` visible.
- Stripe operativo falso.
- Telegram filler.
- Admin con nav cliente.
- OpenAI no configurado mal comunicado.
- Logo cache 0 sin fallback.

## Resultado esperado

Ejecutar `python tools/run_continuous_sentinel_static.py` tras validaciones. Objetivo: score `10.0`, `0 issues reales`.

