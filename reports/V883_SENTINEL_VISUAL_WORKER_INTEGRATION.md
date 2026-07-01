# V883 Sentinel Visual Worker Integration

## Integracion realizada
- `engines/visual_company_worker_engine.py` creado.
- `engines/continuous_shark_sentinel_engine.py` ahora acepta:
  - `mode=visual-worker`
  - `mode=company-worker`
  - `mode=full-company-qa`
- `engines/sentinel_improvement_workflow_engine.py` expone el modelo V883 para tareas, prompts y revalidacion.

## Salidas integradas
- Issues.
- Grouped issues.
- Suggested tasks.
- Codex prompts.
- Safe actions.
- Approval required actions.
- Blocked actions.
- Revalidation notes.

## Seguridad
El ciclo sigue siendo diagnostico y no ejecuta auto-code, auto-deploy, Telegram real, sync proveedor real ni pagos.
