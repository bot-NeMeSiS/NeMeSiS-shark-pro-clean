# V870 Workspace Purge PRO MAX Plan

## No tocar automáticamente
- `.git`.
- `.venv`.
- DB real indicada por `DB_PATH`.
- Usuarios, sesiones, membresías y pagos.
- ZIPs históricos si el usuario quiere conservar trazabilidad.

## Excluir siempre del release
- `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `tmp`, `temp`.
- `release_output`, `releases`, ZIPs internos.
- DB local, WAL, SHM, journal.
- Logs, backups, `.bak`, `.old`, `.orig`.
- Capturas, vídeos y frames pesados.
- `v636work`.
- `.codex`, `.agents`, secretos y tokens.

## Archivable manualmente
- ZIPs antiguos en `release_output`.
- Reportes muy antiguos si ya hay manifest y auditoría.
- Root legacy README/CHANGELOG antiguos.
- Carpetas históricas sin uso como `v636work`.

## Refuerzo aplicado
- `build_clean_release.py` mantiene exclusiones duras y ahora incluye explícitamente reportes V869/V870.
- `audit_release_zip.py` bloquea carpetas prohibidas, ZIPs internos, DBs, logs y media.
- `.gitignore` añade guardrails PRO MAX para backups y frames.

## Próximo paso seguro
Crear una carpeta externa de archivo histórico solo si el usuario lo pide. No mover ni borrar nada sin aprobación.
