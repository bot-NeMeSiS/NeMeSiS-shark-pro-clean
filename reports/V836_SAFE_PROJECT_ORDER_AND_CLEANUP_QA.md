# V836 Safe Project Order And Cleanup QA

## Estrategia

No se borró a ciegas. La limpieza se aplica principalmente al ZIP final mediante `tools/build_clean_release.py` y `tools/audit_release_zip.py`.

## Excluido del ZIP

- `.git`
- `.venv`, `venv`, `env`
- `__pycache__`
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- DB locales y SQLite WAL/SHM
- logs locales
- ZIPs internos
- `release_output` y `releases`
- vídeos/capturas del usuario
- backups y temporales
- archivos con nombres de secretos no permitidos

## Archivos críticos preservados

- `app.py`
- `database_manager.py`
- `templates/`
- `static/`
- `engines/`
- `services/`
- `tools/`
- `requirements.txt`
- `render.yaml`
- `Procfile`
- `.env.example`
- `VERSION.txt`
- `README_MASTER.md`
