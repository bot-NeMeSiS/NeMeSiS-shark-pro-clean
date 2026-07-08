# V917 Runtime Verifier Run QA

- Generado: `2026-07-08T18:37:56+02:00`
- Version: `V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL`

- ok: `False`
- version: `V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL`
- dry_run: `True`
- runtime_url: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
- http_status: `0`
- expected_version: `V917_WORKFORCE_FIRST_FULL_AUTOMATED_RUN_AND_REPORTING_FINAL`
- render_version: `None`
- version_files_match: `None`
- deployment_alignment_status: `None`
- sentinel_active_issues_count: `None`
- secret_masking_ok: `None`
- db_path: `None`
- telegram_configured: `None`
- alignment_status: `DEPLOY_ALIGNMENT_FAILED`
- status: `network_unavailable`
- safe_message: `Runtime verifier no expone secretos y no modifica produccion.`
- next_action: `retry_from_network_enabled_environment`
- report_path: `reports/V917_RUNTIME_VERIFIER_RUN_QA.md`

## Politica
- No expone secretos.
- No envia Telegram real.
- No toca pagos ni DB real destructivamente.
- No declara produccion sin runtime real.
