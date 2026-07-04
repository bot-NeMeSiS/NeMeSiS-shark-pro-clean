# V895 Render V894 Deployment Alignment Report

## Resultado ejecutivo

V895 no introduce una feature nueva. Es un hotfix de alineación para que GitHub `main` y Render desplieguen la versión local correcta en lugar de una versión antigua.

## Local detectado

- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- Versión local antes del hotfix: `V894_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL`
- Versión local V895: `V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL`
- `VERSION.txt`: V895
- `APP_VERSION`: V895
- `app.py`: V895
- Runtime local esperado tras V895: `app_version = V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL`

## Render detectado antes

Endpoint real consultado:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Producción respondió:

- `app_version`: `V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL`
- `version_txt`: `V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL`
- `app_py_path`: `/opt/render/project/src/app.py`
- `current_working_directory`: `/opt/render/project/src`
- `static_app_css_hash`: `a7107f484eaa3dcd`
- `db_path`: `/data/database.db`
- `render_service_hint`: `bot-apuestas-crgf`

Conclusión: Render está sirviendo una raíz/commit anterior. No está sirviendo V894 ni V895.

## ZIP V894 revisado

ZIP usado como base de despliegue limpio:

`release_output\NeMeSiS_SHARK_PRO_V894_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL_RENDER_READY.zip`

Confirmado:

- `app.py` está en raíz.
- `VERSION.txt` está en raíz.
- `requirements.txt` está en raíz.
- `templates/` está en raíz.
- `static/` está en raíz.
- `engines/` está en raíz.
- `tools/` está en raíz.
- `VERSION.txt` dentro del ZIP: V894.
- `APP_VERSION` en `app.py` dentro del ZIP: V894.
- Motores V894 presentes.
- Paneles V894 presentes.
- Herramientas V894 presentes.
- Sin `.git`.
- Sin `.venv`.
- Sin `release_output`.
- Sin ZIPs internos.
- Sin DB local.
- Sin logs.
- Sin secretos reales detectados por estructura.

## Carpeta limpia preparada

Se prepara carpeta local para subir a GitHub copiando contenido interno, no carpeta padre:

`release_output\V895_DEPLOY_ROOT_FROM_V894_ZIP_READY`

Esta carpeta sale del ZIP V894 Render Ready y debe usarse solo como raíz limpia de subida manual.

## Causa probable

El problema no parece estar en el ZIP V894. El ZIP contiene raíz correcta y versión correcta.

La causa probable está en una de estas opciones:

- GitHub `main` no contiene el contenido descomprimido de V894/V895 en la raíz.
- Se subió el ZIP como archivo en vez de subir su contenido interno.
- Se subió una carpeta anidada y Render sigue leyendo otra raíz.
- Render apunta a otro repo.
- Render apunta a otra rama.
- Render tiene `Root Directory` incorrecto.
- Render está desplegando un commit antiguo.
- El deploy no limpió cache.
- El servicio Render correcto no es el que se está desplegando.

## Checklist GitHub

Repo esperado:

`https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`

Rama esperada:

`main`

En GitHub raíz deben verse directamente:

- `app.py`
- `VERSION.txt`
- `APP_VERSION`
- `requirements.txt`
- `templates/`
- `static/`
- `engines/`
- `tools/`

No debe verse en raíz como artefacto de deploy:

- `release_output/`
- `.venv/`
- `.git/`
- DB local
- logs
- ZIPs internos
- `__pycache__/`
- `.pytest_cache/`
- `v636work/`
- carpeta anidada del proyecto

Validación manual mínima:

1. Abrir `VERSION.txt` en GitHub raíz.
2. Confirmar que dice `V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL` si se sube V895, o V894 si se decide subir exactamente el ZIP V894.
3. Abrir `app.py` en GitHub raíz.
4. Confirmar que `APP_VERSION` coincide.

## Checklist Render

Servicio esperado:

`bot-apuestas-crgf`

Configuración esperada:

- Repo: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`
- Branch: `main`
- Root Directory: vacío si el repo usa raíz directa
- Start Command: `gunicorn app:app`
- Build Command: instalar desde `requirements.txt` de la raíz correcta

Pasos exactos:

1. Subir a GitHub el contenido interno del ZIP/carpeta limpia, no la carpeta contenedora.
2. Confirmar `VERSION.txt` y `app.py` en GitHub.
3. Entrar en Render.
4. Abrir servicio `bot-apuestas-crgf`.
5. Confirmar repo, rama y Root Directory.
6. Ejecutar `Manual Deploy -> Clear build cache & deploy`.
7. Esperar `Your service is live`.
8. Abrir `/api/runtime-version`.

## Cómo validar producción

Abrir:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Debe devolver:

- `app_version`: `V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL`
- `runtime_version`: `V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL`
- `version_txt`: `V895_RENDER_V894_DEPLOYMENT_ALIGNMENT_FINAL`
- `version_files_match`: `true`
- `deployment_alignment_status`: `aligned_local_files`
- `has_v895_render_v894_deployment_alignment`: `true`
- `has_v894_autonomous_company_sentinel_workforce`: `true`

Si se despliega V894 exactamente en vez de V895, debe devolver V894 y `has_v894_autonomous_company_sentinel_workforce=true`.

## Si aparece V892, V883 o cualquier versión antigua otra vez

Revisar en este orden:

1. GitHub raíz: `VERSION.txt`.
2. GitHub raíz: `app.py`.
3. GitHub raíz: que no haya carpeta anidada.
4. Render repo conectado.
5. Render branch.
6. Render Root Directory.
7. Render último commit desplegado.
8. Clear build cache.
9. Servicio Render correcto asociado a la URL.

## Honesto

- No se hizo push.
- No se hizo deploy.
- No se tocaron secretos.
- No se enviaron Telegram reales.
- No se tocaron pagos ni DB.
- Render real fue consultado solo por `/api/runtime-version`.
