# V860 Project Cleanup Actions

## Hecho

- Se reforzó `tools/build_clean_release.py` para excluir también `.codex`, `.agents` y journals SQLite.
- Se reforzó `tools/audit_release_zip.py` para validar root requerido y fallar si faltan carpetas base del proyecto.
- Se creó `templates/partials/ui_components.html` para centralizar cards, chips, empty states y botones V860.
- Se añadió una capa CSS V860 dominante para compactar visual, reducir ruido y ocultar duplicidades visibles de navegación admin.
- Se actualizaron `client_app_center`, `picks`, `live`, `admin_company_os`, `admin_company_audit` y `admin_memberships`.

## Limpieza segura permitida

- Se pueden borrar sin riesgo los `__pycache__` fuera de `.venv`.
- Se puede borrar `.pytest_cache`.

## Excluido pero no borrado

- `.venv`
- `release_output/`
- `data/*.db`
- `v636work/`
- ZIPs históricos

## Razón

- Se preserva producción local, `DB_PATH`, sesiones, usuarios y cualquier base real o útil para soporte.
