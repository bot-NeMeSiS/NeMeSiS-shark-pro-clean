# V742 Track Record ROI QA Report

## Cambios

- Track Record calcula métricas reales desde `pick_grading_results` y `picks`.
- Se añaden:
  - stake total;
  - beneficio;
  - ROI;
  - yield;
  - winrate;
  - nulos;
  - pendientes;
  - por mes;
  - por liga;
  - por mercado;
  - por plan.

## Garantía de honestidad

Si no hay resultados evaluables, la pantalla muestra `Pendiente de resultados reales`.

No se inventan porcentajes, beneficios ni resultados.

## QA

- `tools/check_v742_track_record.py`: OK.
- En DB local temporal sin picks, el estado queda en espera y ROI se mantiene pendiente.

## Pendiente

Ejecutar con la DB persistente de Render cuando existan picks cerrados y resultados fiables.
