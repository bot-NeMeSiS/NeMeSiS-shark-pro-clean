# V926 Next Steps

## Deploy

1. Subir el contenido interno de `release_output/V926_DEPLOY_ROOT_CONTENTS` a la raiz del repositorio GitHub.
2. No subir la carpeta padre `V926_DEPLOY_ROOT_CONTENTS` como una carpeta anidada.
3. Confirmar que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/` y `tools/` quedan en raiz.
4. Esperar el deploy de Render.
5. Consultar `/api/runtime-version` y exigir V926, `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.

## Revision en video PC

Revisar a 1366, 1440, 1600 y 1920 px:

- Home: hero compacto y seccion siguiente visible.
- `/app`: seis KPIs y panel de siguiente accion above the fold.
- Calendar/live/picks: filtros y board real visibles antes del scroll largo.
- Admin: sin hueco negro superior, sin hero duplicado y con tablas legibles.
- SHARK/Telegram: columnas equilibradas y estados seguros claros.
- Ausencia de overflow horizontal o textos cortados.

Browser QA con capturas sigue siendo obligatorio antes de cualquier afirmacion pixel-perfect.

