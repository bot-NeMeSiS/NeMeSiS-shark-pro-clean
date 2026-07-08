# V913 Browser QA Execution Or Blocker Status

## Estado

Browser QA no pudo ejecutarse en este entorno porque Playwright no esta instalado.

- Playwright disponible: `false`.
- Chromium disponible: `false`.
- Capturas realizadas: `0`.
- Estado: `PACKAGE_MISSING`.

## Accion preparada

Ejecutar en entorno autorizado:

```powershell
.\browser_qa\run_local_browser_qa.ps1
```

O manualmente:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe tools\run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com --output reports/browser_qa_render --mobile --desktop --write-json
.\.venv\Scripts\python.exe tools\import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
```

No se declara pixel-perfect.
