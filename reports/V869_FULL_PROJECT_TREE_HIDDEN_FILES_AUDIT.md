# V869 Auditoría total de carpetas visibles y ocultas

## CRÍTICO - debe quedarse
- `app.py`, `VERSION.txt`, `APP_VERSION`, `requirements.txt`, `render.yaml`, `Procfile`.
- `templates/`, `static/`, `engines/`, `tools/`, `services/`, `blueprints/`.
- `reports/` actuales de QA y release.
- `.git` si se usa Git localmente.
- `.github` si se usa flujo GitHub.

## ÚTIL local - no debe entrar en release
- `.venv/`: entorno local con Flask usado para checks.
- `.pytest_cache/`, `__pycache__/`: cachés regenerables.
- `release_output/`: histórico de ZIPs Render Ready.
- `data/`: puede contener DBs o datos locales, nunca incluir en ZIP.
- `.agents/`, `.codex/`: contexto local Codex, no release.

## LEGACY - revisar/manual
- `v636work/`.
- READMEs antiguos V5xx/V6xx/V7xx.
- Manifiestos históricos y reportes antiguos.
- Archivos raíz antiguos de engines heredados si ya tienen equivalente en `engines/`.

## BASURA SEGURA - excluir siempre del release
- `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`.
- DBs temporales `tmp_v*.sqlite`.
- Logs, backups, temporales, cachés.
- ZIPs internos.

## PELIGROSO - revisar por datos/secretos
- `.env` real si apareciera.
- DB local, WAL/SHM, SQLite.
- Logs con tokens.
- Capturas o vídeos reales de usuario.

## RELEASE-BLOCKER
- `.git`, `.venv`, `release_output`, `v636work`, DB local, WAL/SHM, logs, ZIPs internos, proyecto anidado, secretos.

## Conclusión
La carpeta oficial local contiene ruido de desarrollo normal en un proyecto largo, pero el release builder y el ZIP audit ya excluyen los bloques peligrosos. V869 refuerza el control con check específico.
