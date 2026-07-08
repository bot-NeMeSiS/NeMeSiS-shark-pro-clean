# V918 Runtime Verifier Run QA

- Generado: `2026-07-08T19:38:52+02:00`
- Version: `V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL`

- ok: `True`
- version: `V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL`
- dry_run: `True`
- runtime_url: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
- http_status: `0`
- expected_version: `V918_WORKFORCE_POST_DEPLOY_BROWSER_QA_ACTIONS_AND_VISUAL_QUEUE_UNLOCK_FINAL`
- render_version: `None`
- runtime_error: `<urlopen error [WinError 10013] Intento de acceso a un socket no permitido por sus permisos de acceso>`
- version_files_match: `None`
- deployment_alignment_status: `None`
- sentinel_active_issues_count: `None`
- secret_masking_ok: `None`
- db_path: `None`
- telegram_configured: `None`
- alignment_status: `NETWORK_UNAVAILABLE_FROM_SHELL`
- status: `network_unavailable_from_shell`
- safe_message: `Runtime verifier no expone secretos y no modifica produccion.`
- next_action: `validate_runtime_from_browser_or_github_action`
- report_path: `reports/V918_RUNTIME_VERIFIER_RUN_QA.md`

## Politica
- No expone secretos.
- No envia Telegram real.
- No toca pagos ni DB real destructivamente.
- No declara produccion sin runtime real.
