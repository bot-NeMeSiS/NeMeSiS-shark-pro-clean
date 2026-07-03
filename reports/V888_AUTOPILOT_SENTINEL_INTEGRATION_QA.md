# V888 AutoPilot Sentinel Integration QA

## Integracion

AutoPilot consume resultados de:

- Continuous Sentinel.
- Sentinel Workflow.
- Visual Company Worker.
- Runtime local.
- Rutas cliente/admin via Flask test client.

Continuous Sentinel expone `sentinel_autopilot_rules_v888` y `sentinel_autopilot_ready`.

## Objetivo

Convertir hallazgos reales en:

- issues;
- tareas;
- prioridades;
- prompts Codex;
- planes de fix seguro;
- acciones que requieren aprobacion.
