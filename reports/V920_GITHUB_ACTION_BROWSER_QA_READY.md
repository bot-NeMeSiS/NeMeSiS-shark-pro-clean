# V920 GitHub Action Browser QA Ready

Version: V920_BROWSER_QA_ARTIFACTS_CAPTURE_OR_UPLOAD_EXECUTION_FINAL

## Workflow revisado

`.github/workflows/browser-qa.yml`

## Estado

- workflow_dispatch: disponible
- Instala dependencias Python: si
- Instala Playwright: si
- Instala Chromium: si
- Ejecuta Browser QA contra `base_url`: si
- Sube artifacts de `reports/browser_qa_render`: si
- No contiene secretos reales: si

## Artifacts esperados

- `reports/browser_qa_render/browser_qa_result.json`
- `reports/browser_qa_render/reference_comparison.json`
- `reports/browser_qa_render/desktop/`
- `reports/browser_qa_render/mobile/`

## Uso recomendado

Actions -> Browser QA -> Run workflow -> `base_url=https://bot-apuestas-crgf.onrender.com`.

Despues descargar artifacts y colocarlos en `reports/browser_qa_render/`, o incorporar el artifact al repo si se decide hacerlo por rama controlada.
