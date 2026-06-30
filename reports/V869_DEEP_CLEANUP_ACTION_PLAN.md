# V869 Deep Cleanup Action Plan

## Aplicado
- Confirmado que `tools/build_clean_release.py` excluye `.git`, `.venv`, cachés, `release_output`, `v636work`, DBs, logs, temporales y ZIPs internos.
- Confirmado que `tools/audit_release_zip.py` falla si aparecen directorios prohibidos, DBs, logs, ZIPs internos o secretos por nombre.
- `.gitignore` ya cubre cachés, DBs, venvs, release_output, ZIPs, logs y secretos habituales.
- Check V869 verifica exclusiones clave.

## No se borra automáticamente
- `.git`: puede ser necesario.
- `.venv`: necesario para validaciones locales.
- `data/`: puede contener DB real o material sensible.
- `release_output/`: histórico útil local, excluido del ZIP.
- `reports/`: evidencias de QA.

## Siguiente limpieza manual recomendada
1. Revisar si `v636work/` sigue aportando valor.
2. Archivar READMEs antiguos fuera del árbol principal si ya no se consultan.
3. Mantener solo los ZIPs más recientes en `release_output` si el usuario quiere aligerar local.
4. Nunca borrar DBs sin confirmar cuál es la real.
