# V913 Next Steps

## Deploy manual

1. Subir el contenido interno de `release_output/V913_DEPLOY_ROOT_CONTENTS` a la raiz del repo GitHub.
2. Confirmar en GitHub raiz:
   - `app.py`
   - `VERSION.txt`
   - `APP_VERSION`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
   - `reports/`
   - `reference_images/`
   - `browser_qa/`
   - `.github/workflows/browser-qa.yml`
3. En Render: `Manual Deploy -> Clear build cache & deploy`.
4. Abrir `/api/runtime-version`.
5. Confirmar que devuelve `V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_AND_RUNTIME_CLEANUP_FINAL`.

## Browser QA real

Ejecutar en PC local o entorno autorizado:

```powershell
.\browser_qa\run_local_browser_qa.ps1
```

Luego volver a desplegar los resultados si se quieren ver en admin/runtime.

## Regla

No declarar pixel-perfect hasta tener capturas reales y comparacion documentada.
