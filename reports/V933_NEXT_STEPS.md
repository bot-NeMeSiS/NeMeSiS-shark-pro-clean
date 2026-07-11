# V933 Next Steps

## Deploy

1. Subir el contenido interno de `release_output/V933_DEPLOY_ROOT_CONTENTS` a la raiz de `main`; no subir la carpeta padre.
2. Confirmar en GitHub que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/` y `tools/` estan en raiz.
3. Esperar el auto-deploy de Render o ejecutar el deploy autorizado.
4. Consultar `/api/runtime-version` hasta obtener V933, `version_files_match=true`, `deployment_alignment_status=aligned_local_files`, `static_css_cache_busting=true` y `service_worker_cache_name=NEMESIS_CACHE_V933`.

## QA post-deploy

Ejecutar Browser QA contra Render y revisar manualmente, como minimo:

- Home, login y registro.
- Cliente: app, calendario, live, picks, historico, SHARK, Telegram, perfil y planes.
- Admin: dashboard, Telegram, usuarios, pagos, picks, datos, Workforce, Sentinel, navegacion y certificacion.
- Desktop: 1366 y 1920 px.
- Mobile: 360, 390 y 430 px.

## Bloqueos honestos

- No declarar pixel-perfect sin revision humana de capturas Render.
- No interpretar estados vacios de DB temporal como falta de producto.
- No ejecutar pagos ni Telegram real durante QA.
- No declarar V933 en produccion hasta que el runtime real la confirme.

