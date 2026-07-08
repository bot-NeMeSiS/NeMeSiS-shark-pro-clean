# V916 Browser QA Activation Guide

## Ruta A - PC local

```powershell
pip install -r browser_qa/playwright_requirements.txt
python -m playwright install chromium
python tools/check_browser_qa_environment.py
python tools/run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com --output reports/browser_qa_render --mobile --desktop --write-json
python tools/import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
```

## Ruta B - GitHub Actions

1. Abrir `Actions`.
2. Ejecutar `Browser QA`.
3. Usar `base_url=https://bot-apuestas-crgf.onrender.com`.
4. Descargar artifacts.
5. Importar resultados si procede.

No se permite declarar igualdad visual sin capturas reales.
