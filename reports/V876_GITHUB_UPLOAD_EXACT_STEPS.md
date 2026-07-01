# V876 GitHub Upload Exact Steps

## Objetivo

Subir V876 correctamente a la raiz del repositorio GitHub usado por Render.

## Pasos exactos

1. Descomprimir el ZIP:
   `NeMeSiS_SHARK_PRO_V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL_RENDER_READY.zip`
2. Entrar dentro de la carpeta descomprimida.
3. Copiar el contenido interno, no la carpeta padre.
4. Pegar ese contenido en la raiz del repo GitHub:
   `bot-NeMeSiS/NeMeSiS-shark-pro-clean`
5. Confirmar que en GitHub raiz se ve:
   - `app.py`
   - `VERSION.txt`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
6. Confirmar que NO se subio:
   - `release_output/`
   - `.venv/`
   - `.git/`
   - DB local, WAL o SHM
   - logs
   - ZIPs internos
   - `__pycache__/`
   - `.pytest_cache/`
   - `v636work/`
7. Abrir en GitHub raiz:
   `VERSION.txt`
8. Confirmar que dice exactamente:
   `V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL`
9. Abrir en GitHub raiz:
   `app.py`
10. Confirmar que contiene:
   `APP_VERSION = 'V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL'`

## Error comun a evitar

No subir el ZIP como archivo. Render no despliega el contenido de un ZIP subido al repo si el codigo real en raiz sigue siendo viejo.

