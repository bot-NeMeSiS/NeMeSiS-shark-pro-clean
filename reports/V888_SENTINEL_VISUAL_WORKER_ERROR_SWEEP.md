# V888 Sentinel Visual Worker Error Sweep

## Actualización V888

Se añadió `V888_REAL_ERRORS_SWEEP_RULES` en `engines/continuous_shark_sentinel_engine.py`.

## Reglas añadidas

- Render/local mismatch debe reportarse.
- Error interno de Telegram Cron debe fallar.
- `QUEUE_SKIPPED` debe estar definido.
- Partidos/live/picks necesitan datos reales o estados seguros.
- Navegación cliente/admin aislada.
- OpenAI ausente debe mostrarse como modo seguro.
- Stripe ausente no debe mostrarse operativo.
- Logo cache cero requiere fallback.
- Mojibake y `None/null/undefined` visibles son incidencias.
- Favicon no debe devolver 404.

## Filosofía

Sentinel no debe maquillar errores reales. Debe servir como empleado de QA, no como sello automático.

