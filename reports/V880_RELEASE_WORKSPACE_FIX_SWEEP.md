# V880 Release Workspace Fix Sweep

## Workspace

El workspace contiene carpetas que no deben entrar en release: `.git`, `.venv`, caches, `release_output`, `v636work`, temporales.

## Corrección

`build_clean_release.py` excluye carpetas/sufijos prohibidos y ahora incluye reportes V880. `audit_release_zip.py` valida raíz y forbidden files.
