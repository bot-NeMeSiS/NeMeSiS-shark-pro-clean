# V876 GitHub Root Deployment QA

## Git local

- `git` no esta disponible en PATH.
- La ruta esperada de GitHub Desktop para `git.exe` no existe en este entorno.
- Se pudo leer `.git/config` directamente.

## Repo configurado localmente

- Remote `origin`: `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`.
- Branch local configurada: `main`.

## Root local

- `app.py` existe en raiz.
- `VERSION.txt` existe en raiz.
- `render.yaml` existe en raiz.
- `Procfile` existe en raiz.
- Hay directorios locales que no deben subirse como release (`.venv`, `release_output`, `tmp`, `v636work`, caches), y el builder los excluye del ZIP.

## QA del ZIP V875 inspeccionado

- `app.py` en raiz: si.
- `VERSION.txt` en raiz: si.
- Version dentro del ZIP: `V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL`.
- APP_VERSION dentro del ZIP: `V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL`.
- Carpeta anidada: no.
- ZIPs internos: no.
- DB local: no.

## Instruccion exacta para deploy manual

1. Descomprimir el ZIP V876 final.
2. Copiar el contenido descomprimido a la raiz del repo `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
3. Verificar en GitHub que `app.py`, `VERSION.txt`, `templates/base.html`, `static/app.css`, `tools/` y `engines/` estan en raiz.
4. Confirmar que no se subio `release_output/`, `.venv/`, `.git/`, DB local, logs ni ZIPs.
5. Confirmar en Render:
   - Branch: `main`.
   - Root Directory: vacio o apuntando exactamente a la raiz que contiene `app.py`.
   - Build Command: `pip install -r requirements.txt`.
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 3 --worker-class gthread --timeout 90`.
6. Ejecutar `Clear build cache & deploy`.
7. Revisar `/api/runtime-version`.

