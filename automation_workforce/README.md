# V915 Automated Company Workforce

Este directorio contiene los workers internos de empresa para preparar, validar y verificar releases de NeMeSiS SHARK PRO.

Politica base:

- Dry-run por defecto.
- No imprime secretos.
- No envia Telegram real.
- No toca pagos reales.
- No modifica DB real destructivamente.
- No declara produccion sin `/api/runtime-version`.

Workers:

- `release_manager.py`: valida release local.
- `render_deploy_guard.py`: prepara o dispara deploy solo con autorizacion explicita.
- `runtime_verifier.py`: compara runtime real contra version esperada.
- `post_deploy_sentinel.py`: smoke post-deploy seguro.
- `browser_qa_orchestrator.py`: coordina Browser QA e import de resultados.
- `visual_queue_manager.py`: clasifica cola visual.
- `telegram_dry_run_watcher.py`: valida Telegram premium/dry-run sin envio real.
- `security_secret_guard.py`: revisa exposicion de secretos.
- `reporting_worker.py`: consolida reportes V915.

Activacion de deploy automatizado:

1. Configurar secretos en GitHub o Render, nunca en el repo.
2. Definir `ENABLE_AUTOMATED_RENDER_DEPLOY=1`.
3. Definir `RENDER_DEPLOY_HOOK_URL` o `RENDER_API_KEY` + `RENDER_SERVICE_ID`.
4. Ejecutar workflow manual `render-deploy.yml`.

Si falta cualquier secreto, el deploy no se dispara y se genera reporte seguro.
