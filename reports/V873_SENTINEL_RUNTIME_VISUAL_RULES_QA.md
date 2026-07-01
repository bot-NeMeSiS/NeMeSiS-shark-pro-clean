# V873 Sentinel runtime visual rules QA

## Reglas revisadas

- `last_error` crudo en runtime.
- OpenAI no configurado sin comunicación segura.
- Cache de logos a cero sin fallback.
- Botones repetidos.
- Admin con nav cliente.
- Mobile overflow.
- Stripe operativo falso.
- Telegram filler.
- Apuestas garantizadas.

## Resultado esperado

Ejecutar `tools/run_continuous_sentinel_static.py` tras V873. Objetivo: score 10.0, 0 issues reales, 0 críticos.

## Resultado local V873

- Score: `10.0`.
- Issues: `0`.
- Críticos: `0`.
- Modo: `quick`, `dry_run=true`.
- Browser real: no ejecutado en modo static.
