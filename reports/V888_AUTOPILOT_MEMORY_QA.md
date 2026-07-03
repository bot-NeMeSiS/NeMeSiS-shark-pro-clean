# V888 AutoPilot Memory QA

## Memoria

AutoPilot usa archivo controlado:

`data/runtime/sentinel_autopilot_memory.json`

Solo se escribe cuando se ejecuta un scan autorizado desde admin o cron protegido. No se escribe durante render visual de cliente.

## Campos soportados

- `issue_id`
- `title`
- `category`
- `severity`
- `screen`
- `route`
- `evidence`
- `detected_at_madrid`
- `status`
- `suggested_fix`
- `codex_prompt`
- `safe_to_auto_fix`
- `requires_approval`
- `source`
- `resolved_at`
- `version_detected`
- `render_version`

## Politica

No guarda secretos, tokens, pagos sensibles, usuarios completos ni datos deportivos inventados.
