# V924 Deploy Readiness With V923 Client Hotfix QA

## Versiones

- Version local: `V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`
- `VERSION.txt`: `V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`
- `APP_VERSION`: `V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`
- Render real antes del deploy V924: `V923_CLIENT_ROUTES_INTERNAL_ERROR_RECOVERY_AFTER_V922_FINAL`
- Estado de produccion V924: no declarado hasta que `/api/runtime-version` devuelva V924.

## Hotfix V923 preservado

V924 conserva los guards del hotfix cliente V923:

- `has_v923_client_routes_internal_error_recovery = true`
- `has_v923_v922_client_regression_fix = true`
- `has_v923_sports_routes_safe_render_guard = true`
- `has_v923_client_login_health_guard = true`

El check `tools/check_v923_client_routes_internal_error_recovery.py` acepta V924 como version contenedora y valida que el fix de rutas cliente sigue activo.

## Flags V924 confirmados

- `has_v924_global_empty_space_fix = true`
- `has_v924_client_value_upgrade = true`
- `has_v924_sports_data_odds_safe_context = true`
- `has_v924_admin_command_center_compact_fix = true`
- `has_v924_home_duplicate_hero_fix = true`

## Smoke de rutas cliente

Resultado local con Flask test client:

- `/` = 200
- `/cliente-login` = 200
- `/login` = 200
- `/registro` = 200
- `/app` = 302 controlado a `/cliente-login?next=/app`, no 500
- `/calendar` = 200
- `/calendario` = 200
- `/live` = 200
- `/directo` = 200
- `/picks` = 200
- `/shark` = 200
- `/telegram` = 302 controlado a `/cliente-login?next=/telegram`, no 500
- `/profile` = 302 controlado a `/cliente-login`, no 500
- `/support` = 200

## Rutas admin y sistema

- `/admin-login` = 200
- `/admin/dashboard` = 302 protegido a login, no 500
- `/admin/automation-workforce` = 302 protegido a login, no 500
- `/api/runtime-version` = 200
- `/ruta-inventada` = 404 premium
- `/api/ruta-inventada` = JSON 404 seguro
- `/manifest.json` = 200
- `/service-worker.js` = 200 y contiene `NEMESIS_CACHE_V924`

## QA visual seguro V924

- Home duplicate hero fix: confirmado por marcador `v924-legacy-public-hero-hidden` y `data-v924-hidden="duplicate-public-hero"`.
- Admin empty space fix: confirmado por `v924-admin-shell`, `v924-section-compact` y capa CSS `/* V924 global UI empty-space and product value fix */`.
- Cliente value upgrade: `/app`, `/calendar`, `/live`, `/picks`, `/shark` y `/telegram` conservan estados seguros y clases V924.
- Datos deportivos: V924 usa contexto seguro/cacheado o estados vacios; no inventa partidos, cuotas, picks, resultados ni ROI.
- Pixel-perfect: no declarado. Sigue dependiendo de Browser QA real.

## Validaciones ejecutadas

- `python -m py_compile app.py tools/check_v923_client_routes_internal_error_recovery.py tools/check_v924_global_ui_sports_value_fix.py`
- `python -m compileall app.py engines tools automation_workforce`
- `python tools/check_madrid_times.py`
- `python tools/check_v923_client_routes_internal_error_recovery.py`
- `python tools/check_v924_global_ui_sports_value_fix.py`
- `python tools/run_continuous_sentinel_static.py`
- `python tools/print_release_identity.py`
- `python tools/check_deploy_root_identity.py`
- `python tools/audit_all_routes_links.py`
- Smoke Flask de rutas cliente/admin/sistema

## Deploy root y ZIP

Artefactos esperados:

- ZIP: `release_output/NeMeSiS_SHARK_PRO_V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL_RENDER_READY.zip`
- Deploy root: `release_output/V924_DEPLOY_ROOT_CONTENTS`

La raiz del deploy debe contener directamente:

- `app.py`
- `VERSION.txt`
- `requirements.txt`
- `templates/`
- `static/`
- `engines/`
- `tools/`
- `reports/`
- `reference_images/`
- `browser_qa/`
- `automation_workforce/`
- `.github/workflows/`

No debe subirse una carpeta padre accidental ni incluir `.git`, `.venv`, DB local, logs, ZIPs internos, `.env` real o secretos.

## Pasos exactos para deploy

1. Abrir `release_output/V924_DEPLOY_ROOT_CONTENTS`.
2. Copiar el contenido interno de esa carpeta, no la carpeta contenedora.
3. Pegar ese contenido en la raiz del repo GitHub `bot-NeMeSiS/NeMeSiS-shark-pro-clean`, rama `main`.
4. Confirmar en GitHub que `VERSION.txt` y `app.py` muestran `V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`.
5. En Render, lanzar deploy manual o esperar auto-deploy.
6. Abrir `/api/runtime-version` y confirmar:
   - `version = V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`
   - `version_files_match = true`
   - `deployment_alignment_status = aligned_local_files`
   - flags V923 y V924 activos.
7. Probar `/cliente-login`, `/app`, `/calendar`, `/live`, `/picks`, `/admin/dashboard` y la home publica.

## Resultado

V924 queda lista para deploy sin perder el hotfix V923. No se declara V924 en produccion hasta que Render lo confirme.
