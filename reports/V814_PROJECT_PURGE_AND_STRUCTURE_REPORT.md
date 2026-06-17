# V814 Project Purge and Structure Report

## Limpieza aplicada

V814 no elimina de forma agresiva archivos dudosos. La carpeta oficial contiene mucha historia del proyecto, y parte puede ser útil para trazabilidad. La limpieza real para producción se garantiza en el ZIP Render Ready.

## Excluido del ZIP final

El builder excluye:

- `.git/`
- `.venv/`, `venv/`, `env/`
- `__pycache__/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `release_output/`, `releases/`
- `logs/`, `backups/`, `tmp/`, `temp/`
- `v636work/`
- `.db`, `.sqlite`, `.sqlite3`, WAL/SHM
- `.log`
- `.zip`
- vídeos `.mp4`, `.mov`, `.avi`, `.mkv`
- nombres sensibles con `secret`, `token`, `private_key`, `id_rsa`, salvo `.env.example` y `.env.render.clean`

## Duplicados detectados

- Módulos en raíz con equivalentes dentro de `engines/` o `services/`.
- Informes históricos en raíz y dentro de `reports/`.
- ZIPs antiguos en `release_output/`.
- Cachés y entorno virtual local.

## Revisión manual recomendada

Mover o archivar en una versión futura:

- módulos legacy de raíz si se confirma que no se importan;
- informes V5xx-V6xx antiguos si se quiere una carpeta comercial más limpia;
- `v636work/` si ya no se necesita como respaldo histórico.

## Estructura final recomendada

- `app.py`
- `database_manager.py`
- `engines/`
- `services/`
- `templates/`
- `static/`
- `tools/`
- `tests/`
- `blueprints/`
- `docs/`
- `reports/`
- `requirements.txt`
- `Procfile`
- `render.yaml`
- `.env.example`
- `.env.render.clean`
- `VERSION.txt`
- `README_MASTER.md`
