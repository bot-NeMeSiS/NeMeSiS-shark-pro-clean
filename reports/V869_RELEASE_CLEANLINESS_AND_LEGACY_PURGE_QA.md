# V869 Release Cleanliness and Legacy Purge QA

## Release limpio
V869 refuerza la separación entre carpeta local ruidosa y ZIP Render Ready limpio.

## Excluido por builder/auditoría
- `.git`
- `.venv`
- `__pycache__`
- `.pytest_cache`
- `release_output`
- `releases`
- `v636work`
- DB local, WAL/SHM
- logs
- ZIPs internos
- temporales
- secretos por nombre

## No borrado
No se borró nada a ciegas. La limpieza real de histórico debe hacerse manualmente si el usuario quiere aligerar la carpeta local.
