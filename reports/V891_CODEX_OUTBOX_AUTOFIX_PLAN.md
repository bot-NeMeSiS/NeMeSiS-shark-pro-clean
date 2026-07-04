# V891/V893 Codex Outbox And Autofix Plan

## Outbox

El worker genera prompts Codex revisables en:

- `data/runtime/autonomous_sentinel/outbox/codex_prompts.md`
- `data/runtime/autonomous_sentinel/outbox/<issue_id>_codex_prompt.md`

## Autofix

El motor `sentinel_autofix_planner_engine.py` separa:

- `SAFE_AUTOFIX`: cambios de copy/estado seguros.
- `DANGEROUS_REQUIRES_CODEX`: rutas, seguridad, datos, pagos, Telegram, secretos, deploy o DB.

## Regla operativa

Por defecto no se aplican cambios automaticamente. El sistema se mantiene en modo planificacion y revision.

## Acciones bloqueadas

- deploy automatico.
- push automatico.
- Telegram real.
- pagos reales.
- borrado de DB/usuarios.
- exposicion de secretos.
