# V829 GitHub Render Codex Workflow

## Fuente de verdad

Usar siempre:

`C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`

No usar ZIPs antiguos como base si contienen `.git`, `.venv`, cachés, DB local, logs, ZIPs internos, `release_output` viejo o proyecto anidado.

## ZIP limpio

El ZIP final se genera con:

`python tools/build_clean_release.py`

Y se audita con:

`python tools/audit_release_zip.py`

Debe quedar `forbidden_count=0`.

## GitHub

Si GitHub Desktop muestra archivos basura, no subir:

- `.venv`
- `.git`
- `__pycache__`
- `.pytest_cache`
- DBs locales
- logs
- ZIPs antiguos
- vídeos/capturas
- `release_output`

Subir cambios reales de código, templates, static, tools, reports y manifest.

## Render

Verificar:

- `/api/runtime-version`.
- `/api/automation/master-tick` sin secret = 403.
- `/api/automation/master-tick?secret=...&dry_run=1` = 200.
- `/api/automation/health-check?secret=...` = 200.
- `DB_PATH=/data/database.db` en producción.

## Mobile QA

Probar en navegador con 390px y 430px:

- `/app`
- `/partidos`
- `/live`
- `/picks`
- `/shark`
- `/profile`
- `/telegram`
- `/support`

## Secretos

No incluir secretos en informes, ZIPs ni screenshots.
