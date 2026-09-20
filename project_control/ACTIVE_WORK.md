# Active Work

Actualizado 2026-09-20. Base efectiva: `main@bf0a36dd1f2ff928d143ae6ac0254bf20f991529`.

## 1. OPS-001 — Sentinel operational closure

Estado: DONE_LOCAL_SAFE.

Cierre: `reports/SENTINEL_OPERATIONAL_CLOSURE_20260920.md`.
Sentinel queda disponible como QA/observabilidad local, con executor productivo explícitamente NO habilitado.

## 2. Sports Reality / Directos

Estado: IN_PROGRESS / INTEGRATED_WITH_GAPS.

El antiguo PR #14 esta superseded. Main ya contiene su actualizacion en pagina abierta y mejoras posteriores.
Pendiente:
- certificacion productiva del comportamiento en navegador;
- feed/proveedor real y frescura;
- cobertura de estados limite;
- no confundir tests/fixtures con proveedor real.

## 3. Resultados

Estado: IN_MAIN_WITH_GAPS.

Calendario ya puede hidratar resultados persistidos de una fecha pasada mediante lectura local.
Mantener resultados deportivos por fecha separados de Track Record/ROI.
Pendiente: cobertura real del proveedor/retencion y QA productiva de fechas con datos existentes.
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
