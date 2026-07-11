# V931 Next Steps

## Despliegue

1. Subir el contenido interno de `release_output/V931_DEPLOY_ROOT_CONTENTS` a la raiz de `main`.
2. Confirmar en GitHub que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/` y `tools/` estan directamente en la raiz.
3. No subir la carpeta padre `V931_DEPLOY_ROOT_CONTENTS` como un directorio anidado.
4. Esperar el auto-deploy de Render o iniciarlo manualmente desde Render si procede.
5. Consultar `https://bot-apuestas-crgf.onrender.com/api/runtime-version` hasta obtener V931, `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.

## Comprobacion post-deploy

1. Abrir `/cliente-login` sin sesion y con una sesion cliente valida.
2. Abrir `/app`, `/calendar`, `/calendario`, `/live`, `/directo`, `/picks` y `/track-record`.
3. Confirmar que ninguna ruta devuelve 500/502 ni queda bloqueada por proveedor.
4. Confirmar que `Partidos hoy` coincide con el numero de cards validas de hoy.
5. Confirmar que no aparecen como partidos completos registros sin competicion, fecha, hora o fuente.
6. Revisar Sentinel y comprobar 0 incidencias activas nuevas.

## Estado de produccion

V931 solo puede declararse en produccion cuando el runtime real de Render devuelva exactamente `V931_PRODUCTION_CLIENT_ROUTES_AND_HOME_DATA_CONSISTENCY_HOTFIX_FINAL`.

No continuar con redisenio hasta cerrar esta comprobacion post-deploy.
