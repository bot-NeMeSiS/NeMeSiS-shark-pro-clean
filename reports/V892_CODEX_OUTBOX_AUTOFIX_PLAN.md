# V892/V894 Codex Outbox And Autofix Plan

## Outbox

Los prompts Codex se guardan en:

- `data/runtime/autonomous_company_sentinel/codex_outbox.md`
- `data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md`
- `data/runtime/autonomous_company_sentinel/outbox/SENT-XXXX_codex_prompt.md`

## Autofix

SAFE_AUTOFIX puede planificar cambios seguros de copy, estados vacios, fallback visual y CSS menor. Por defecto no aplica cambios.

REQUIRES_CODEX cubre login, sesiones, pagos, DB_PATH, migraciones, Telegram real, Render Cron, secretos, APIs deportivas, deploy y push.

## Regla

`AUTONOMOUS_SENTINEL_AUTOFIX=0` por defecto.
