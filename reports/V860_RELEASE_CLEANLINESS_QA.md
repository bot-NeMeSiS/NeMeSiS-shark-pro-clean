# V860 Release Cleanliness QA

## Objetivo

- ZIP final sin `.git`, `.venv`, `__pycache__`, `.pytest_cache`, DB local, WAL/SHM, logs, ZIPs internos ni proyecto nested.

## Refuerzos V860

- `build_clean_release` ahora excluye también `.codex`, `.agents`, `.db-journal` y `.sqlite-journal`.
- `audit_release_zip` ya no solo busca basura: también exige root mínimo (`app.py`, `VERSION.txt`, `requirements.txt`, `templates`, `static`, `engines`, `tools`, `reports`).

## Riesgos todavía fuera del source limpio

- `release_output/` conserva 59 ZIPs históricos locales.
- `data/` conserva 54 DBs locales y de validación.
- `.venv/` conserva muchos `__pycache__`.

## Decisión

- Excluir del release por defecto.
- Limpiar físicamente solo caches seguras fuera de `.venv` y sin tocar `data/`.
