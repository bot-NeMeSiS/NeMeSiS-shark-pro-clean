# V878 Workspace Cleanup Controlled Plan

## Hallazgos locales

El workspace contiene carpetas y archivos que no deben entrar al ZIP final:

- `release_output/`
- `.venv/`
- `.git/`
- `tmp/`
- `v636work/`
- `__pycache__/`
- `.pytest_cache/`
- DBs temporales

## Accion V878

Se mantiene y refuerza la exclusion mediante `tools/build_clean_release.py` y auditoria ZIP.

## No se borra automaticamente

- `.git`
- `.venv`
- DB real o local sin autorizacion
- `release_output`
- capturas/reportes historicos

## Limpieza manual recomendada

Cuando el usuario lo autorice, revisar `tmp/`, DBs temporales y capturas pesadas fuera del ZIP.

