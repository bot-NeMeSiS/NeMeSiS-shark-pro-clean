# V915 Runtime Verification Pre-Deploy

- Version local esperada: `V915_AUTOMATED_COMPANY_WORKFORCE_RENDER_DEPLOY_PIPELINE_FINAL`
- Produccion real conocida antes del deploy V915: `V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_AND_RUNTIME_CLEANUP_FINAL`
- Estado esperado ahora: mismatch controlado hasta que Damian suba V915 y Render haga deploy.

## Que verifica el worker

- `version`
- `app_version`
- `version_txt`
- `runtime_version`
- `version_files_match`
- `deployment_alignment_status`
- `sentinel_active_issues_count`
- `secret_masking_ok`
- `db_path`
- Telegram masked state

## Nota de entorno

En esta sesion local, las llamadas de red desde scripts pueden estar bloqueadas por permisos del entorno. La verificacion real de Render debe repetirse tras deploy desde navegador, GitHub Action o entorno con red autorizada.

