# V903 Deploy Root Alignment QA

## Repo local
- Remoto detectado: `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`.
- Rama detectada: `main`.
- Raiz local contiene `app.py`, `VERSION.txt`, `APP_VERSION`, `requirements.txt`, `templates/`, `static/`, `engines/`, `tools/`, `reports/` y `reference_images/`.

## Deploy root
La carpeta final esperada tras build es:
`release_output/V903_DEPLOY_ROOT_CONTENTS`

Debe copiarse el contenido interno a la raiz de GitHub, no la carpeta padre.

## Render
Render debe usar:
- Repo correcto.
- Rama `main`.
- Root Directory vacio o apuntando a la raiz real.
- Start Command `gunicorn app:app`.
- Manual Deploy con Clear build cache.

## Estado
Render actual no debe declararse V903 hasta que `/api/runtime-version` devuelva V903.
