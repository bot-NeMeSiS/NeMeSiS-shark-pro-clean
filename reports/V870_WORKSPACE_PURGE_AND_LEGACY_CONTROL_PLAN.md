# V870 Workspace Purge and Legacy Control Plan

## Mantener
- `app.py`, `VERSION.txt`, `APP_VERSION`.
- `templates/`, `static/`, `engines/`, `tools/`, `services/`, `blueprints/`.
- `requirements.txt`, `Procfile`, `render.yaml`, `runtime.txt`.
- Reportes recientes V862-V870.
- Docs actuales útiles.

## Excluir siempre del release
- `.git`, `.venv`, `__pycache__`, `.pytest_cache`.
- `release_output`, `releases`, ZIPs internos.
- DB local, WAL/SHM, SQLite.
- logs, caches, tmp/temp, backups.
- vídeos y capturas pesadas.
- `v636work`.
- proyecto anidado y secretos.

## Archivar/revisar manual
- Root legacy `.py` antiguos que duplican engines.
- READMEs/CHANGELOGs históricos.
- Patches antiguos.
- Reports muy antiguos o pesados.

## Acción aplicada
No se borró nada. V870 refuerza auditoría y checks para que lo local no contamine el ZIP Render Ready.
