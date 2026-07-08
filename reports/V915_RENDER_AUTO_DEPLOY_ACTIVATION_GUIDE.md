# V915 Render Auto Deploy Activation Guide

V915 deja preparado deploy automatico seguro, pero no lo ejecuta sin autorizacion.

## Opcion A - Render Auto Deploy normal

1. Abrir `release_output/V915_DEPLOY_ROOT_CONTENTS`.
2. Copiar el contenido interno, no la carpeta padre.
3. Pegar/subir ese contenido a la raiz del repo GitHub `bot-NeMeSiS/NeMeSIS-shark-pro-clean` o equivalente correcto.
4. Confirmar que en GitHub raiz existen `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/`, `tools/`, `reports/`, `reference_images/`, `browser_qa/`, `automation_workforce/` y `.github/workflows/`.
5. Si Render tiene auto-deploy activo para `main`, esperar build/deploy.
6. Abrir `/api/runtime-version` y confirmar V915.

## Opcion B - GitHub Action + Render Deploy Hook

1. En Render, crear o copiar el Deploy Hook del servicio.
2. En GitHub: Settings -> Secrets and variables -> Actions.
3. Crear el secret `RENDER_DEPLOY_HOOK_URL`.
4. No pegar ese valor en chats, capturas ni reportes.
5. Ejecutar manualmente el workflow `Render Deploy Guard`.
6. El workflow dispara el hook sin imprimirlo y luego verifica `/api/runtime-version`.

## Opcion C - Render API avanzado

1. Configurar `RENDER_API_KEY` y `RENDER_SERVICE_ID` como secrets.
2. Mantener `ENABLE_AUTOMATED_RENDER_DEPLOY=0` por defecto.
3. Activarlo solo cuando Damian autorice explicitamente.

## Confirmacion final

No declarar V915 en produccion hasta que Render devuelva:

`V915_AUTOMATED_COMPANY_WORKFORCE_RENDER_DEPLOY_PIPELINE_FINAL`

