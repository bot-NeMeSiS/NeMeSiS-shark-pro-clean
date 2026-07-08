# V911 Next Steps

Version: `V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL`

## Deploy

1. Subir el contenido interno de `release_output/V911_DEPLOY_ROOT_CONTENTS` a la raiz del repo GitHub.
2. Confirmar `VERSION.txt` y `APP_VERSION` en V911.
3. En Render: `Manual Deploy -> Clear build cache & deploy`.
4. Confirmar `/api/runtime-version` con `V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL`.

## QA after deploy

- Abrir `/admin/shark-sentinel` y comprobar que no aparece `Salir cliente`.
- Abrir `/admin/autonomous-company-sentinel` y comprobar KPIs separados.
- Abrir `/admin/sentinel-codex-outbox` y revisar Visual Fix Queue.
- Ejecutar Browser QA real cuando Playwright este disponible.

## Browser QA command

```powershell
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe tools\run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com --output reports/browser_qa_render --mobile --desktop --write-json
```
