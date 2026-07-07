# V902 Render Deploy Alignment Confirmation

Fecha local: 2026-07-07.

## ZIP V902 revisado

ZIP:

`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\release_output\NeMeSiS_SHARK_PRO_V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL_RENDER_READY.zip`

Resultado:

- ZIP existe: sí.
- `app.py` en raíz del ZIP: sí.
- `VERSION.txt` en raíz del ZIP: sí.
- `requirements.txt` en raíz del ZIP: sí.
- `templates/`, `static/`, `engines/`, `tools/`, `reports/`, `reference_images/` en raíz: sí.
- Carpeta padre anidada dentro del ZIP: no.
- ZIPs internos: no.
- `VERSION.txt`: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- `APP_VERSION` en `app.py`: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- Flag runtime V902 presente: `has_v902_sentinel_full_active_issues_fix`.

## Carpeta limpia preparada

Carpeta:

`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\release_output\V902_DEPLOY_ROOT_CONTENTS`

La raíz queda así:

- `V902_DEPLOY_ROOT_CONTENTS\app.py`
- `V902_DEPLOY_ROOT_CONTENTS\VERSION.txt`
- `V902_DEPLOY_ROOT_CONTENTS\requirements.txt`
- `V902_DEPLOY_ROOT_CONTENTS\templates\`
- `V902_DEPLOY_ROOT_CONTENTS\static\`
- `V902_DEPLOY_ROOT_CONTENTS\engines\`
- `V902_DEPLOY_ROOT_CONTENTS\tools\`
- `V902_DEPLOY_ROOT_CONTENTS\reports\`
- `V902_DEPLOY_ROOT_CONTENTS\reference_images\`

No queda así:

- `V902_DEPLOY_ROOT_CONTENTS\NeMeSiS_SHARK_PRO_V902...\app.py`

Limpieza confirmada:

- `.git`: no.
- `.venv`: no.
- `__pycache__`: no.
- `.pytest_cache`: no.
- DB local: no.
- logs: no.
- `release_output` viejo: no.
- ZIPs internos: no.
- `.env` real: no.
- secretos: no detectados por auditoría ZIP.

## Git local

Repo local detectado en `.git/config`:

`https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`

Rama local detectada en `.git/HEAD`:

`main`

Git CLI:

- `git` global no disponible en PowerShell.
- GitHub Desktop git en la ruta comprobada no disponible.
- No se hizo push.
- No se inventan PRs, commits ni estado remoto.

## Render real antes

Endpoint consultado:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado real observado:

- `app_version`: `V897_SENTINEL_TRUTHFUL_ISSUES_ROUTE_ALIAS_REFERENCE_QA_FIX_FINAL`.
- `version`: `V897_SENTINEL_TRUTHFUL_ISSUES_ROUTE_ALIAS_REFERENCE_QA_FIX_FINAL`.
- `version_files_match`: `true`.
- `deployment_alignment_status`: `aligned_local_files`.
- `app_py_path`: `/opt/render/project/src/app.py`.
- `db_path`: `/data/database.db`.

Nota: aunque el prompt indicaba producción en V901, la consulta real actual devuelve V897. Por tanto producción todavía no sirve V902.

## Runtime local

Runtime local verificado:

- `app_version`: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- `version`: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- `version_txt`: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- `runtime_version`: `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`.
- `version_files_match`: `true`.
- `deployment_alignment_status`: `aligned_local_files`.
- `has_v902_sentinel_full_active_issues_fix`: `true`.

## Validaciones locales mínimas

Pasadas:

- `python -m py_compile app.py`.
- `python -m compileall app.py engines tools`.
- `python tools/check_madrid_times.py`.
- `python tools/check_v902_sentinel_full_active_issues_fix.py`.
- `python tools/run_continuous_sentinel_static.py`.
- `audit_release_zip`: `forbidden_count=0`, `missing_required_root=[]`.

## Push/deploy

- Push automático: no ejecutado.
- Deploy automático: no ejecutado.
- Secretos tocados: no.
- DB real tocada: no.
- Telegram real enviado: no.
- Pagos reales tocados: no.

## Pasos exactos para Damian

1. Abrir:

   `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\release_output\V902_DEPLOY_ROOT_CONTENTS`

2. Copiar el contenido interno de esa carpeta, no la carpeta `V902_DEPLOY_ROOT_CONTENTS`.

3. Pegar/subir ese contenido en la raíz del repo GitHub:

   `bot-NeMeSiS/NeMeSiS-shark-pro-clean`

   Rama:

   `main`

4. Confirmar en GitHub raíz que existen directamente:

   - `app.py`
   - `VERSION.txt`
   - `requirements.txt`
   - `templates/`
   - `static/`
   - `engines/`
   - `tools/`
   - `reports/`
   - `reference_images/`

5. Abrir en GitHub `VERSION.txt` y confirmar:

   `V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`

6. Abrir en GitHub `app.py` y confirmar:

   `APP_VERSION = 'V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL'`

7. En Render:

   - Servicio: `bot-apuestas-crgf`.
   - Repo esperado: `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`.
   - Rama: `main`.
   - Root Directory: vacío o raíz correcta.
   - Start Command: `gunicorn app:app`.

8. Ejecutar:

   `Manual Deploy -> Clear build cache & deploy`

9. Esperar a que Render diga que el servicio está live.

10. Abrir:

   `https://bot-apuestas-crgf.onrender.com/api/runtime-version`

11. Confirmar:

   - `version = V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`
   - `app_version = V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`
   - `version_txt = V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`
   - `runtime_version = V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL`
   - `version_files_match = true`
   - `deployment_alignment_status = aligned_local_files`
   - `has_v902_sentinel_full_active_issues_fix = true`

## Si Render sigue en V897/V901

Diagnóstico probable:

- GitHub `main` no recibió V902 en la raíz.
- Se subió la carpeta padre en vez del contenido interno.
- Render apunta a otro repo.
- Render apunta a otra rama.
- Root Directory apunta a una subcarpeta antigua.
- No se ejecutó `Clear build cache & deploy`.
- Render desplegó un commit viejo.
- `VERSION.txt` o `app.py` siguen antiguos en GitHub raíz.

