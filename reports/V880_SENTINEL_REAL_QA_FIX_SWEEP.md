# V880 Sentinel Real QA Fix Sweep

## Reglas añadidas

`V880_PROBLEM_SWEEP_RULES` detecta:

- Render/local mismatch.
- Runtime last_error activo.
- API configurada sin datos visibles.
- Partidos/live vacíos sin explicación.
- Picks sin cuota/selección sin estado.
- Logo cache 0 sin fallback.
- Admin/cron sin protección.
- Traceback/debug visible.
- ZIP con basura.
- Checks antiguos rechazando versión nueva.

## Resultado

Sentinel conserva score 10 local, pero ahora informa reglas más cercanas a problemas reales de producto.
