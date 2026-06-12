# V577 — Smart Pick Grading & Auto Validation

Avance incremental sobre V576 sin rehacer la app.

## Añadido

- Motor `engines/pick_grading_engine.py`.
- Tablas seguras:
  - `pick_grading_results`
  - `pick_grading_runs`
- Validación inteligente de picks con marcador final cuando el mercado es fiable.
- Modo conservador: si no puede validar con seguridad, deja el pick en revisión.
- Profit estimado por cuota/stake.
- Ajuste de confianza antes/después para SHARK.
- APIs admin:
  - `/api/pick-grading/summary`
  - `/api/pick-grading/run`
- Integración visual en `/admin/data-center`.

## Filosofía

No inventa resultados. No toca picks salvo que el admin marque aplicar y el motor tenga evidencia suficiente.

Objetivo:

Partido finalizado → Pick → Resultado fiable → Validación → Memoria SHARK → Mejor recomendación futura.
