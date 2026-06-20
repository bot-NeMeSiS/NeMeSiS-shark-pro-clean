# V833 GitHub Render Workflow Final QA

## Fuente de verdad

Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.

## GitHub

`.git` existe. Branch detectada: `main`. Remote origin: `https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean.git`.

El comando `git` no está disponible en PATH en esta ejecución, por lo que no se hizo commit ni push. Usar GitHub Desktop para crear rama/commit/push si procede. Rama sugerida: `v833-reference-ecosystem-visual-completion`.

## Render

Verificar tras deploy: `/api/runtime-version`, `/api/health`, `/api/automation/health-check?secret=...` y `/api/automation/master-tick?secret=...&dry_run=1`.

## No subir

No subir `.env`, DB locales, `.venv`, cachés, logs, ZIPs antiguos, capturas, vídeos ni `release_output`.

## Rollback

Revertir commit en GitHub o usar ZIP limpio anterior auditado. No usar ZIPs no auditados.
