# V902B Deploy Alignment And Secret Rotation Guard

## Estado
- Versión local preparada: `V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL`.
- Base preservada: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- Producción real consultada: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
- Render real sigue sirviendo: `V897_SENTINEL_TRUTHFUL_ISSUES_ROUTE_ALIAS_REFERENCE_QA_FIX_FINAL`.

## Diagnóstico
Render no está ejecutando el código local actual. El deploy real todavía apunta a una versión anterior del árbol de proyecto, por lo que no se puede certificar V902/V902B en producción hasta subir el contenido correcto a la raíz del repositorio y ejecutar `Clear build cache & deploy`.

## Corrección V902B
- `VERSION.txt`, `APP_VERSION` y `APP_VERSION` en `app.py` pasan a V902B.
- `/api/runtime-version` añade `has_v902b_deploy_alignment_secret_rotation_guard`.
- El runner `tools/render_cron_telegram_tick.py` deja de mostrar los últimos caracteres del secreto.
- Los estados de secretos se exponen solo como `***configured***`, `***missing***` o `***hidden***`.
- Los runbooks/reportes con ejemplos antiguos de secretos quedan saneados.

## Rotación recomendada
El valor de `AUTOMATION_SECRET` debe considerarse comprometido si apareció en una URL real compartida, captura, log público o chat. La acción segura es rotarlo en Render Web Service y en Render Cron Job con el mismo valor nuevo, sin pegarlo en reportes ni commits.

## Próximo paso
Subir el contenido raíz del ZIP/carpeta V902B a GitHub, confirmar `VERSION.txt` y `app.py` en raíz, ejecutar `Manual Deploy -> Clear build cache & deploy` y volver a consultar `/api/runtime-version`.

## Validación local final
- `py_compile`: OK.
- `compileall`: OK.
- Madrid Time: OK.
- Check V902 compatibilidad: OK.
- Check V902B secret/deploy guard: OK.
- Sentinel static: score `10.0`, `0` issues.
- Parseo Jinja: `168` templates OK.
- Smoke local: runtime `200`, master tick sin secret `403`, Telegram tick sin secret `403`, health-check con secret local falso `200`.
- ZIP audit: `forbidden_count=0`, `missing_required_root=[]`.
- Carpeta de deploy preparada: `release_output/V902B_DEPLOY_ROOT_CONTENTS`.

## No realizado
- No se hizo push.
- No se hizo deploy.
- No se rotó ningún secreto desde Codex.
- No se envió Telegram real.
- No se tocaron pagos, DB ni usuarios.
