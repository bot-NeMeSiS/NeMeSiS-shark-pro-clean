# V915 Post-Deploy Sentinel Plan

Ejecutar despues de desplegar V915.

## Checks

- `/api/runtime-version` devuelve V915.
- `version_files_match=true`.
- `deployment_alignment_status=aligned_local_files`.
- `/` responde 200.
- `/admin-login` responde 200.
- `/ruta-inventada` devuelve 404 premium.
- `/api/ruta-inventada` devuelve JSON seguro.
- `/manifest.json` responde 200.
- `/service-worker.js` responde 200.
- Telegram cron sin secret devuelve 403.
- Browser QA status queda claro.
- Visual queue status queda claro.

## Prohibido

- No enviar Telegram real.
- No tocar pagos.
- No tocar DB real destructivamente.
- No exponer secretos.

## Worker

```bash
python automation_workforce/post_deploy_sentinel.py --dry-run
```
