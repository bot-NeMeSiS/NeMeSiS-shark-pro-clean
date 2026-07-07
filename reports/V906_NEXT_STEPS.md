# V906 Next Steps

1. Desplegar V906 solo cuando se suba el contenido de `release_output/V906_DEPLOY_ROOT_CONTENTS`.
2. Confirmar `/api/runtime-version` en Render con V906.
3. Instalar Playwright/Chromium en un entorno autorizado.
4. Ejecutar:

`python tools/run_browser_reference_qa.py --base-url http://127.0.0.1:5000 --output reports/V906_browser_qa --mobile --desktop --admin-safe --no-login-required --timeout 15000`

5. Revisar capturas contra `reference_images/`.
6. Aplicar solo correcciones visuales evidenciadas por captura.
