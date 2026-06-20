# V832 GitHub Render Codex Automation Workflow

## Fuente de verdad

Usar siempre: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.

No trabajar sobre ZIPs antiguos mezclados. El ZIP final de `release_output` sirve como release auditada, no como workspace diario salvo recuperación.

## Codex

Antes de cambios: confirmar `VERSION.txt`, `APP_VERSION`, `/api/runtime-version` y último ZIP limpio. Después: ejecutar compileall, smoke, checks y ZIP auditado.

## GitHub

Git no está disponible en PATH en esta ejecución. La carpeta sí tiene `.git`, branch local `main` y remote origin `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`.

Usar GitHub Desktop si hace falta:

1. Abrir la carpeta oficial.
2. Revisar que no se incluyan `.env`, `.db`, `.venv`, cachés, logs, ZIPs ni capturas.
3. Crear rama `v832-full-app-reference-workflow-final`.
4. Commit normal.
5. Push normal.
6. Abrir PR si procede.

## Render

Render debe desplegar desde GitHub o desde el ZIP limpio auditado. Verificar después del deploy:

- `/api/runtime-version`
- `/api/health`
- `/api/automation/health-check?secret=...`
- `/api/automation/master-tick?secret=...&dry_run=1`

## Rollback

Usar commit anterior en GitHub o ZIP limpio anterior. No usar ZIPs no auditados.
