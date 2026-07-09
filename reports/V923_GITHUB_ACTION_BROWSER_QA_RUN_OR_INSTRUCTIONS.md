# V923 GitHub Action Browser QA Run Or Instructions

status: GITHUB_ACTION_MANUAL_RUN_REQUIRED
github_action_available: true
executed_by_codex: false

## Instrucciones
1. Abrir GitHub -> Actions.
2. Elegir Browser QA.
3. Run workflow.
4. Usar base_url = https://bot-apuestas-crgf.onrender.com.
5. Descargar el artifact generado.
6. Copiar su contenido dentro de reports/browser_qa_render/.
7. Ejecutar:
```powershell
.\.venv\Scripts\python.exe tools\import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data
```

No se usaron tokens ni secretos.

