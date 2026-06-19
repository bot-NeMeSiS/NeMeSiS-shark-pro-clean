# V815 Render Runtime Visibility Audit

Version: `V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`

## Resultado

V815 queda certificada para distinguir si Render sirve la version nueva o una version antigua/cacheada.

## Versiones detectadas

- `VERSION.txt`: `V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`
- `app.py / APP_VERSION`: `V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`
- Raiz real local: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- `DB_PATH` se mantiene: `/data/database.db`

## Templates reales por ruta cliente

| Ruta | Template real |
| --- | --- |
| `/` | `templates/home.html` |
| `/app` | `templates/client_app_center.html` |
| `/calendar` | `templates/calendar.html` |
| `/partidos` | `templates/calendar.html` |
| `/live` | `templates/live.html` |
| `/picks` | `templates/picks.html` |
| `/match/<id>` | `templates/match_detail.html` |
| `/shark` | `templates/shark.html` |
| `/profile` / `/perfil` | `templates/profile.html` |
| `/telegram` | `templates/telegram.html` |

## CSS y cache-busting

- `templates/base.html` carga `static/app.css` con:
  `?v=V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`
- El HTML incluye:
  - `<meta name="nemesis-version" content="V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED">`
  - `data-v815-shell="true"`
  - `<!-- NEMESIS V815 CLIENT SHELL ACTIVE -->`
- `static/app.css` contiene capa V815 activa por `body[data-v815-shell="true"]`.
- Hash local CSS reportado por check: `f43de7f0a2b10da6`.

## Endpoint runtime

`/api/runtime-version` devuelve:

- `app_version`
- `version_txt`
- `python_file_path`
- `current_working_directory`
- `template_base_detected`
- `has_v815_shell`
- `static_css_hash`
- `static_css_size`
- `generated_at`
- `render_service_hint`
- `db_path`
- flags sin secretos para API-Football, Telegram, The Odds API y `AUTOMATION_SECRET`.

## Estructura del ZIP

El builder mantiene `app.py`, `templates/` y `static/` en raiz del ZIP. `release_output/`, ZIPs internos, DB locales, caches, `.git`, `.venv`, `.orig`, `.bak`, `.old`, `.tmp` y backups quedan excluidos.

## Por que Render podria no mostrar cambios

1. Render esta desplegando un ZIP anterior o una rama distinta.
2. El ZIP se subio con carpeta anidada incorrecta en vez de raiz con `app.py`.
3. El navegador conserva CSS viejo.
4. Render no hizo `Clear build cache & deploy`.
5. El servicio no apunta a este artefacto V815.
6. Se abre una ruta distinta a las modificadas.

## Como comprobarlo

1. Abrir `/api/runtime-version`.
2. Confirmar `app_version = V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`.
3. Confirmar `has_v815_shell = true`.
4. Abrir codigo fuente de `/app` y buscar `NEMESIS V815 CLIENT SHELL ACTIVE`.
5. Confirmar que `app.css` carga con `?v=V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`.
