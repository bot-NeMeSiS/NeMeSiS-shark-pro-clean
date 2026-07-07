# V903 Next Steps

## Paso 1
Copiar el contenido interno de `release_output/V903_DEPLOY_ROOT_CONTENTS` a la raiz del repo GitHub.

## Paso 2
Confirmar en GitHub:
- `VERSION.txt` = `V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL`.
- `APP_VERSION` = `V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL`.
- `app.py` contiene `APP_VERSION` V903.

## Paso 3
En Render:
- `Manual Deploy -> Clear build cache & deploy`.
- Confirmar `/api/runtime-version` = V903.

## Paso 4
Rotar `AUTOMATION_SECRET` en Render Web Service y Cron Job si el secreto pudo quedar expuesto.

## Paso 5
Ejecutar Browser QA real con capturas PC/movil para cerrar gaps visuales pendientes.

## Estado final local V903
- No se hizo push ni deploy automatico.
- Produccion no se declara V903 hasta que `/api/runtime-version` lo confirme.
- Render real observado al cierre de esta preparacion: `V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL`.
- Accion principal: subir el contenido de `release_output/V903_DEPLOY_ROOT_CONTENTS` a la raiz del repo, limpiar cache de build en Render y desplegar.
