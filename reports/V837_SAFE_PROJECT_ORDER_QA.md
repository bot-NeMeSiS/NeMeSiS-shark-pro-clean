# V837 Safe Project Order QA

## Regla

No se borró a ciegas. La limpieza se aplica en el ZIP final con `tools/build_clean_release.py` y `tools/audit_release_zip.py`.

## Excluido del ZIP

- `.git`
- `.venv`, `venv`, `env`
- cachés
- logs
- DB locales, WAL y SHM
- ZIPs internos
- `release_output`
- vídeos/capturas del usuario
- secretos

## Preservado

`app.py`, `templates/`, `static/`, `engines/`, `services/`, `tools/`, `requirements.txt`, `render.yaml`, `Procfile`, `.env.example`, `VERSION.txt`.
