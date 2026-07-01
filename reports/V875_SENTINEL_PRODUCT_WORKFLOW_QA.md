# V875 Sentinel Product Workflow QA

## Objetivo

Sentinel debe funcionar como empleado de QA: detectar problemas accionables, priorizar y revalidar.

## Reglas a mantener

- Mojibake.
- `None/null/undefined` visible.
- Botones duplicados.
- Stripe operativo falso.
- Telegram filler.
- Picks sin estado seguro.
- OpenAI no configurado mal comunicado.
- Logos cache 0 sin fallback.

## Estado V875

Sentinel local debe mantenerse en score alto. La validacion final se ejecuta con `tools/run_continuous_sentinel_static.py`.

