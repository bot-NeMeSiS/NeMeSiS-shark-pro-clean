# Active Work

Actualizado 2026-09-20. Base efectiva: `main@7a1ba50bf9d6fec8648fcacc2dae72b7cbe730ba`.

## 1. OPS-001 — Sentinel operational closure

Estado: PRODUCTION_VALIDATION / LOCAL_SAFE.

Objetivo inmediato:
- confirmar que el codigo integrado conserva el limite LOCAL SAFE;
- revisar persistencia y fronteras de escritura del runner;
- mantener Sentinel como QA/observabilidad y no como executor productivo;
- reconciliar estados de Project Control con GitHub/Render actuales;
- no crear scheduler, worker autonomo productivo ni permisos nuevos.

Evidencia actual:
- CI y smoke verdes en main;
- preflight productivo verde;
- Secret Guard, rutas, Jinja, navegacion y Continuous Sentinel verdes;
- runner LOCAL SAFE separado en CI para no contaminar otros tests.

## 2. Sports Reality / Directos

Estado: INTEGRATED_WITH_GAPS.

El antiguo PR #14 esta superseded. Main ya contiene su actualizacion en pagina abierta y mejoras posteriores.
Pendiente:
- certificacion productiva del comportamiento en navegador;
- feed/proveedor real y frescura;
- cobertura de estados limite;
- no confundir tests/fixtures con proveedor real.

## 3. Resultados

Estado: QA / pendiente de profundizacion.

Mantener resultados deportivos por fecha separados de Track Record/ROI.
No inventar resultados ni convertir ausencia de score en 0-0.

## 4. Design

Estado: PRESERVE / QA.

R8 y trabajo visual integrado se conservan. R9/H07 y conformidad global siguen NOT_CERTIFIED.
No abrir otra capa visual antes de medir el estado real de main.

## 5. Rendimiento y comercial

- `/app`: medir produccion real antes de afirmar mejora.
- Stripe/pagos: NOT_CERTIFIED.
- ELITE+: no definido.
- Proveedor profundo API-Football: PARTIAL / ACCESS_FAILED en evidencia persistida; no usarlo como fuente certificada.

## Regla de continuacion

Todo trabajo nuevo parte de main actual. No reabrir PR #14/#15 ni reutilizar sus heads como base.
