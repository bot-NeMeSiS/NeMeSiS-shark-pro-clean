# Final Bug Backlog

## Executive Summary

No se corrigio codigo durante lockdown porque no aparecio una regresion confirmada que justificara tocar producto. Este backlog recoge bloqueos y riesgos reales con evidencia.

## Backlog Priorizado

| ID | Prioridad | Estado | Area | Evidencia | Correccion minima |
| --- | --- | --- | --- | --- | --- |
| RL-001 | P1 | OPEN | Git/Release | Working tree local con cambios y archivos sin seguimiento | Cierre Git selectivo por sprint, sin mezclar artefactos |
| RL-002 | P1 | OPEN | Cron | runtime: v937_sports_cron_status=PARTIAL | Diagnosticar subtarea que causa PARTIAL y registrar resultado real |
| RL-003 | P1 | OPEN | Master Tick | runtime: v937_cron_master_status=NOT_RECORDED | Confirmar endpoint/job y persistir ultimo tick observable |
| RL-004 | P1 | OPEN | Restore | No existe restore aislado ejecutado en este sprint | Ensayo de restauracion con backup no productivo |
| RL-005 | P1 | OPEN | Stripe | CONFIGURED_PENDING_NON_DESTRUCTIVE_PRODUCTION_EVIDENCE | Prueba controlada de checkout/webhook sin cobro real |
| RL-006 | P1 | OPEN | Telegram | Runtime configurado, local dry-run MISSING_BOT_TOKEN | Prueba controlada con destino autorizado/enmascarado y sin spam |
| RL-007 | P2 | OPEN | UX/Product | Experience Platform: 32 P2 estaticos | Revisar falsos positivos y corregir solo UX visible confirmada |
| RL-008 | P3 | OPEN | UX/Product | Experience Platform: 170 P3 estaticos | Agrupar en backlog de polish post-lockdown |
| RL-009 | P2 | OPEN | QA Artifact | Primer Browser QA fallo al escribir captura antigua en PRODUCT_FINALIZATION | Usar carpetas por ejecucion o limpiar artefactos bloqueados antes de QA |
| RL-010 | P3 | OPEN | Legacy checks | smoke_check advierte endpoints V601/V602 ausentes | Actualizar expectativas antiguas o documentar deprecacion |
| RL-011 | P2 | OPEN | Operacion local | Aviso: no ADMIN local ni ADMIN env completas | Definir bootstrap seguro de admin para QA local |

## Bugs Corregidos Durante Lockdown

Ninguno.

## Riesgos No Convertidos en Bug

- Decision Engine informa LOW_EVIDENCE_CONFIDENCE. Es un estado honesto por evidencia limitada, no un fallo.
- Telegram local MISSING_BOT_TOKEN no contradice runtime Render configurado; indica diferencia de entorno local.
- Stripe real_charge=false es correcto y esperado porque no se ejecutaron pagos reales.

## Criterio de Cierre

El backlog de lockdown se considera cerrado cuando:

1. Git queda limpio.
2. Cron deportivo pasa de PARTIAL a PASS o se documenta la causa aceptada.
3. Master Tick deja de estar NOT_RECORDED.
4. Restore aislado se prueba.
5. Stripe y Telegram tienen certificacion no destructiva.
6. P2 de Experience Platform quedan revisados y clasificados.
