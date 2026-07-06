# V898 Outbox Sentinel Truth QA

## Problema

El outbox podía conservar prompts de fallos antiguos, por ejemplo rutas 500, aunque el último smoke ya devolviera 200/302.

## Solución

`engines/sentinel_codex_outbox_engine.py` separa:

- prompts activos;
- `Prompts archivados / obsoletos`.

`engines/autonomous_company_sentinel_engine.py` añade:

- `active_issues_open`;
- `stale_issues`;
- `resolved_by_rescan`;
- `archived_prompts`.

## Resultado

Los prompts obsoletos no deben mezclarse con tareas activas para Codex.

