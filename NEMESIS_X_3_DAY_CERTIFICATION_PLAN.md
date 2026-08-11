# NEMESIS X 3 DAY CERTIFICATION PLAN

Objetivo: certificar REAL_DAY_1, REAL_DAY_2 y REAL_DAY_3 sin intervencion humana.

## Estado actual

La certificacion temporal local de 3 dias es PASS. No equivale todavia a ejecucion real de calendario en Render.

## Checklist para certificacion real

1. Mantener Git limpio y sin cambios pendientes no revisados.
2. Ejecutar `tools/run_continuous_evolution_scheduler.py --dry-run --task daily_product_review`.
3. Confirmar due/not due sin escribir estado.
4. Autorizar un mecanismo externo read-only para invocar el runner una vez al dia.
5. No activar Telegram, Stripe, deploy, fuentes externas ni mutaciones de usuarios.
6. Registrar REAL_DAY_1 con job log PASS o PARTIAL controlado.
7. Confirmar Founder Brief del dia siguiente.
8. Repetir para REAL_DAY_2.
9. Repetir para REAL_DAY_3.
10. Verificar que no existen duplicados, locks bloqueados, secretos impresos ni cambios de produccion.

## Evidencia requerida por dia

- job_id;
- scheduled_for;
- trigger;
- started_at;
- finished_at;
- duration;
- status;
- run_id;
- snapshot_id;
- Founder Brief;
- comparison against previous;
- Product Memory updated;
- Codex Inbox prepared;
- no Telegram;
- no Stripe;
- no deploy;
- no production mutation.

## Criterio PASS real

Los tres dias deben mostrar ejecucion programada real con status PASS o PARTIAL seguro, sin intervencion humana y sin acciones mutantes.
