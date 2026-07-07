# V907 Playwright Install Guide

## Local Authorized Environment

Playwright no se instala automaticamente salvo que el entorno lo autorice. Para activarlo manualmente:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

Luego ejecutar:

```powershell
.\.venv\Scripts\python.exe tools\run_browser_reference_qa.py --base-url http://127.0.0.1:5000 --output reports/V907_browser_qa --mobile --desktop --admin-safe --no-login-required --write-json
```

## Optional Dependency File

Se creo:

```text
requirements-browser.txt
```

Contenido:

```text
playwright
```

No se anade Playwright a `requirements.txt` para no convertirlo en dependencia obligatoria de produccion Render.

## CI / GitHub Actions Option

En un entorno CI autorizado:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python tools/run_browser_reference_qa.py --base-url http://127.0.0.1:5000 --output reports/V907_browser_qa --mobile --desktop --admin-safe --no-login-required --write-json
```

## Rule

Sin capturas reales no se declara pixel-perfect ni cierre visual definitivo.

