# V815 Root Version Runtime Audit

Version final: `V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`

## Auditoria de raiz

- Carpeta oficial usada: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- `app.py` existe en la raiz real.
- `templates/`, `static/`, `engines/` y `tools/` existen en la raiz real.
- El builder genera el ZIP con `app.py` en raiz, no dentro de `NeMeSiS shark pro/app.py`.
- `release_output/` queda excluido del ZIP final.

## Versiones

- `VERSION.txt`: `V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`
- `APP_VERSION`: `V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`
- Estado: coinciden.

## Runtime visible

`/api/runtime-version` devuelve campos de certificacion:

- `app_version`
- `version_txt`
- `app_py_path`
- `current_working_directory`
- `template_base_path`
- `has_v815_shell`
- `has_v815_css`
- `static_app_css_hash`
- `static_app_css_size`
- `static_app_css_mtime`
- `build_generated_at` mediante `generated_at`
- `db_path`
- flags sin secretos para API-Football, The Odds API, Telegram y `AUTOMATION_SECRET`.

## CSS

- `base.html` carga:
  `/static/app.css?v=V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`
- `static/app.css` contiene marcador V815 y reglas activadas por `data-v815-shell`.
- Cache-busting obligatorio presente.

## Marcas en HTML fuente

- Meta version V815 presente.
- `data-v815-shell="true"` presente.
- Comentario fuente presente:
  `<!-- NEMESIS V815 CLIENT SHELL ACTIVE -->`

## Basura y mezcla historica

La carpeta real conserva informes y capas historicas V797/V805/V812/V813/V814 porque forman parte de la evolucion acumulada, pero el ZIP final excluye `.git`, `.venv`, caches, DB locales, logs, ZIPs internos, `.orig`, `.bak`, `.old`, `.tmp`, videos y temporales.

## Riesgo Render

Si Render no muestra V815 despues del deploy, las causas probables son:

1. Render esta ejecutando un ZIP anterior.
2. El ZIP fue subido con raiz anidada incorrecta.
3. No se hizo `Clear build cache & deploy`.
4. El navegador mantiene CSS viejo.
5. Se esta mirando otro servicio/URL.

La prueba definitiva es `/api/runtime-version`.
