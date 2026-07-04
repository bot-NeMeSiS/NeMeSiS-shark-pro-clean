# V891/V893 Autonomous Sentinel User/Admin Reference QA Worker

## Resultado

Se implementa como V893 porque la base local ya estaba en V892 y no conviene retroceder versionado. Se preserva el flag solicitado:

- `has_v891_autonomous_sentinel_user_admin_reference_worker`
- `has_v893_autonomous_sentinel_worker`

## Qué se añade

- Worker autonomo seguro en `engines/autonomous_sentinel_worker_engine.py`.
- QA de journeys cliente/admin en `engines/sentinel_user_journey_engine.py`.
- QA de brecha visual/referencias en `engines/sentinel_reference_qa_engine.py`.
- Planificador de autofix seguro en `engines/sentinel_autofix_planner_engine.py`.
- Panel admin `/admin/autonomous-sentinel` con alias `/admin/sentinel-worker`, `/admin/qa-worker` y `/admin/revision-automatica`.
- APIs admin protegidas para estado, ultima ejecucion, incidencias, outbox, autofix plan y ejecucion dry-run.
- Cron protegido `/api/automation/autonomous-sentinel/run`.

## Seguridad

El worker no hace deploy, no hace push, no envia Telegram real, no toca pagos reales, no borra usuarios, no borra DB y no llama APIs caras. Solo revisa rutas, genera incidencias y escribe memoria operativa local en `data/runtime/autonomous_sentinel`.

## Integracion

El worker sincroniza hallazgos con el centro comun de incidencias Sentinel y genera prompts Codex accionables en outbox para que el usuario pueda revisar antes de aplicar cambios.
