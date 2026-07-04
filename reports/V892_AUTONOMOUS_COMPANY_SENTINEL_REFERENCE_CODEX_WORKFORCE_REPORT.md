# V892/V894 Autonomous Company Sentinel Reference Codex Workforce

## Resultado

Se implementa la peticion V892 sobre base local V893 como version ascendente:

- `V894_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL`

Se preservan los flags solicitados:

- `has_v892_autonomous_company_sentinel`
- `has_v892_reference_qa_worker`
- `has_v892_codex_outbox`
- `has_v892_safe_autofix_planner`
- `has_v892_user_admin_journey_worker`

## Creado

- Motor central: `engines/autonomous_company_sentinel_engine.py`
- Journey user/admin: `engines/sentinel_user_admin_journey_engine.py`
- Referencias visuales: `engines/sentinel_reference_visual_engine.py`
- Outbox Codex: `engines/sentinel_codex_outbox_engine.py`
- Autofix seguro: `engines/sentinel_safe_autofix_engine.py`
- Render alignment: `engines/sentinel_render_alignment_engine.py`
- Watch Telegram: `engines/sentinel_telegram_quality_watch_engine.py`

## Paneles

- `/admin/autonomous-company-sentinel`
- `/admin/company-sentinel`
- `/admin/auto-qa`
- `/admin/sentinel-empresa`
- `/admin/autonomous-sentinel`
- `/admin/sentinel-codex-outbox`

## Cron

- `/api/automation/autonomous-company-sentinel/run`

Sin secret devuelve 403. Con secret valido y `dry_run=1` devuelve 200 y no ejecuta acciones peligrosas.

## Seguridad

No hace deploy, push, Telegram real, pagos reales, mutaciones de DB real ni llamadas caras a proveedores deportivos. No inventa partidos, picks, cuotas, resultados ni escudos.
