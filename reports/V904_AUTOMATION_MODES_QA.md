# V904 Automation Modes QA

## Base

- Version local: `V904_AUTONOMOUS_REFERENCE_GAPS_REBUILD_AND_SENTINEL_WORKFORCE_FINAL`.
- Objetivo: dejar preparado un flujo automatico permanente, seguro y controlado para que Sentinel Empresa revise el producto sin tocar datos reales.
- Produccion no debe declararse V904 hasta que `/api/runtime-version` en Render devuelva V904.

## Modos preparados

### reference_scan

Endpoint:

`/api/automation/autonomous-company-sentinel/run?mode=reference_scan&dry_run=1`

Lee:

- Sentinel.
- `reference_images/`.
- `reference_manifest.json`.
- Codex outbox.
- Gaps visuales.

Escribe:

- `data/runtime/autonomous_company_sentinel/latest_run.json`.
- `data/runtime/autonomous_company_sentinel/reference_gap_report.json`.
- `data/runtime/autonomous_company_sentinel/outbox/codex_outbox.md`.

Seguridad:

- No toca datos reales.
- No envia Telegram real.
- No gasta APIs caras.
- No expone secretos.
- No hace deploy ni push.

### daily_reference_review

Endpoint:

`/api/automation/autonomous-company-sentinel/run?mode=daily_reference_review&dry_run=1`

Revisa:

- Admin.
- Cliente.
- Picks.
- Live.
- Calendario.
- SHARK.
- Telegram.
- PWA/404.
- Outbox Codex.
- Rutas criticas.

### post_deploy_check

Endpoint:

`/api/automation/autonomous-company-sentinel/run?mode=post_deploy_check&dry_run=1`

Revisa:

- `/api/runtime-version`.
- Version esperada.
- `admin-login`.
- Rutas cliente.
- Rutas admin.
- Telegram dry-run.
- 404 premium.
- Service worker.
- `reference_images/`.
- Outbox.
- Sentinel active issues.

## Render Cron

Render Cron evalua horarios en UTC. Ajustar la hora en Dashboard usando UTC, no Europe/Madrid.

Revision diaria:

`curl -fsS "https://bot-apuestas-crgf.onrender.com/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=daily_reference_review&dry_run=1&runner=render_cron"`

Revision post-deploy:

`curl -fsS "https://bot-apuestas-crgf.onrender.com/api/automation/autonomous-company-sentinel/run?secret=$AUTOMATION_SECRET&mode=post_deploy_check&dry_run=1&runner=render_cron"`

No pegar el valor real de `AUTOMATION_SECRET` en chats, capturas, reportes ni logs.

## Politica de acciones

El sistema separa cualquier hallazgo en:

- `SAFE_AUTOFIX`: acciones seguras y reproducibles.
- `CODEX_PROMPT_REQUIRED`: requiere intervencion Codex antes de tocar codigo.
- `HUMAN_APPROVAL_REQUIRED`: secretos, pagos, Telegram real, DB, usuarios, sesiones, deploy, push o cambios peligrosos.

## Panel admin

`/admin/autonomous-company-sentinel` muestra:

- Ultima revision automatica.
- Modo ejecutado.
- Gaps leidos.
- Gaps abordados.
- Prompts activos.
- Errores activos.
- Estado deploy.
- Estado secret masking.
- Proximo paso recomendado.

## Resultado

V904 queda preparado para operar como worker permanente de revision: detecta, clasifica, genera prompts y deja evidencia, pero no ejecuta acciones peligrosas solo.
