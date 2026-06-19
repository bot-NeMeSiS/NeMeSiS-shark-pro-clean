# V816 Real Source of Truth Audit

Version: `V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL`

## Fuente oficial

La fuente oficial es la carpeta:

`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`

No se debe desplegar el ZIP grande antiguo ni carpetas anidadas. El ZIP correcto es el generado por `tools/build_clean_release.py` en `release_output`.

## Version real

- `VERSION.txt`: `V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL`
- `APP_VERSION`: `V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL`
- Estado: coinciden.

## Runtime

`/api/runtime-version` expone:

- `app_version`
- `version_txt`
- `app_py_path`
- `current_working_directory`
- `template_base_path`
- `has_v816_shell`
- `has_v816_css`
- `has_v815_shell`
- `static_app_css_hash`
- `static_app_css_size`
- `static_app_css_mtime`
- `static_css_cache_busting`
- `build_generated_at`
- `db_path`
- flags sin secretos para API-Football, The Odds API, Telegram y `AUTOMATION_SECRET`.

## Por que un ZIP anterior podia parecer V805

La carpeta historica conserva artefactos y versiones antiguas, y el usuario tambien tiene ZIPs grandes externos. Si se sube un ZIP incorrecto o anidado, Render puede ejecutar otro `app.py` con `APP_VERSION` antiguo. V816 evita esto generando un ZIP limpio con `app.py`, `templates/`, `static/`, `engines/` y `tools/` en raiz.

## Que ZIP subir

`NeMeSiS_SHARK_PRO_V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL_RENDER_READY.zip`

## Que no subir

- ZIP grande antiguo.
- Carpeta completa con `.git`, `.venv`, caches o `release_output`.
- Cualquier ZIP que al abrirlo contenga `NeMeSiS shark pro/app.py` en vez de `app.py` en raiz.

## Limpieza del ZIP

El builder excluye `.git`, `.venv`, caches, DB locales, logs, ZIPs internos, `release_output`, videos, `.bak`, `.orig`, `.old`, `.tmp` y backups.

## Resultado final verificado

- ZIP final generado en `release_output/NeMeSiS_SHARK_PRO_V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL_RENDER_READY.zip`.
- Auditoria independiente del ZIP: `forbidden_count = 0`.
- Raiz del ZIP verificada: incluye `app.py`, `templates/base.html`, `static/app.css`, `reports/V816_*`, `tools/check_v816_*` y `RELEASE_MANIFEST_V816.json`.
- No hay proyecto anidado dentro del ZIP final.
- `/api/runtime-version` y `tools/check_v816_runtime_visibility.py` confirman V816, hash/tamano de CSS y cache-busting V816.
