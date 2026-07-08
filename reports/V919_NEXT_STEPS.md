# V919 Next Steps

## Estado actual

- Browser QA JSON exists.
- Valid screenshot count is 0.
- Visual queue remains blocked.
- Pixel-perfect claim is not allowed.

## Proxima accion requerida

run_browser_qa_or_upload_artifacts

## Opciones

1. Run Browser QA locally with Playwright and Chromium.
2. Run the GitHub Action browser-qa workflow.
3. Upload/import Browser QA artifacts that include real desktop/mobile screenshot files.

After screenshots exist, run:

`.venv\Scripts\python.exe tools\import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data`

Then refresh the visual queue and only unlock items with screenshot evidence.
