# V909 Render Deploy Alignment Confirmation

## Version local

- VERSION.txt: `V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`
- APP_VERSION: `V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`
- ZIP V909: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\release_output\NeMeSiS_SHARK_PRO_V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL_RENDER_READY.zip`
- Deploy root: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\release_output\V909_DEPLOY_ROOT_CONTENTS`

## Version Render real antes y estado actual

- Endpoint consultado: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`
- Version Render real antes indicada por Damian: `V908_SCREENSHOT_BASED_REFERENCE_UI_FIX_PASS_FINAL`
- Version real observada el 2026-07-07 tras consultar runtime: `V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`
- Estado actual: Render ya sirve V909 con `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.
- Nota de honestidad: V909 solo debe declararse en produccion mientras `/api/runtime-version` siga devolviendo V909.

## Raiz correcta confirmada en deploy root

Debe verse directamente dentro de `V909_DEPLOY_ROOT_CONTENTS`, no dentro de una carpeta padre:

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

## Limpieza confirmada

La carpeta deploy root no debe contener:

- `.git`
- `.venv`
- `DB local`
- `logs`
- `ZIPs internos`
- `release_output viejo`
- `.env real`
- `secretos`

## Correcciones preservadas

- V902B secret masking: preservado por flags/checks locales.
- V906B portada limpia: preservado por check V906B/V908/V909 compatible.
- V907 Browser QA readiness: preservado por check V907.
- V908 visual fix pass: preservado por check V908.
- reference_images y reference_manifest: presentes en deploy root y ZIP.
- Sentinel funcional: `score 10.0`, `0 issues` en validacion local.

## Pasos exactos para subir V909 a GitHub

1. Abrir `release_output/V909_DEPLOY_ROOT_CONTENTS`.
2. Seleccionar el contenido interno de esa carpeta, no la carpeta `V909_DEPLOY_ROOT_CONTENTS` como carpeta padre.
3. Copiar ese contenido a la raiz del repo GitHub `bot-NeMeSiS/NeMeSiS-shark-pro-clean`, rama `main`.
4. Confirmar en la raiz de GitHub que se ven directamente:
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
5. Abrir `VERSION.txt` en GitHub y confirmar que dice exactamente `V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`.
6. Abrir `app.py` en GitHub y confirmar `APP_VERSION = 'V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL'`.
7. No subir `release_output/`, `.venv/`, `.git/`, DB local, logs, ZIPs internos ni `.env` real.

## Pasos exactos en Render

1. Abrir servicio Render `bot-apuestas-crgf`.
2. Confirmar repo correcto y rama `main`.
3. Confirmar Root Directory vacio o apuntando a la raiz real del proyecto.
4. Confirmar Start Command: `gunicorn app:app`.
5. Ejecutar `Manual Deploy -> Clear build cache & deploy`.
6. Esperar `Your service is live`.
7. Abrir `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
8. Confirmar:
   - `version = V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`
   - `app_version = V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`
   - `runtime_version = V909_BROWSER_QA_EXECUTION_PIPELINE_AND_VISUAL_FIX_QUEUE_FINAL`
   - `version_files_match = true`
   - `deployment_alignment_status = aligned_local_files`
   - `has_v909_browser_qa_pipeline = true`
   - `has_v909_visual_fix_queue = true`

## Si Render sigue sin V909

Revisar:

- GitHub no recibio V909 en raiz.
- Se subio la carpeta padre en vez del contenido interno.
- Render apunta a otro repo o rama.
- Root Directory incorrecto.
- Build cache no se limpio.
- GitHub Desktop no hizo commit/push real.
- Existe otro servicio Render asociado a la URL.

## Nota final

No se hizo push ni deploy automatico. V909 no debe declararse en produccion hasta que `/api/runtime-version` devuelva V909.
