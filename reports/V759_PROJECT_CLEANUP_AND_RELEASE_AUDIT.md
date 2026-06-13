# V759 PROJECT CLEANUP AND RELEASE AUDIT

## Basura detectada en la carpeta local

- `.git`: se conserva localmente, se excluye del ZIP.
- `.venv`: se conserva localmente, se excluye del ZIP.
- `.pytest_cache`: se excluye.
- `__pycache__`: se excluye.
- `release_output`: contiene ZIPs antiguos, se excluye del ZIP final.
- `v636work`: carpeta heredada, se excluye.
- ZIPs internos detectados en `release_output`: excluidos.

## Estado de bases de datos locales

No se detectaron `.db`, `.sqlite` o `.sqlite3` locales dentro del árbol visible durante la auditoría.

## Política de ZIP limpio

`tools/build_clean_release.py` excluye:

- `.git`
- `.venv`
- `venv`
- `__pycache__`
- `.pytest_cache`
- `.mypy_cache`
- `.ruff_cache`
- `node_modules`
- `release_output`
- `releases`
- `backups`
- `logs`
- archivos `.db`, `.sqlite`, `.sqlite3`
- logs
- vídeos
- ZIPs internos
- nombres sensibles salvo `.env.example` y `.env.render.clean`

## Qué se deja por compatibilidad

- Informes históricos en raíz.
- `docs/` con README antiguos.
- `tests/` y herramientas de checks.
- `blueprints/` y `services/`.

## Confirmación

La limpieza principal se aplica en el empaquetado Render Ready. No se borran piezas dudosas del workspace para evitar pérdida accidental de contexto o documentación histórica.
