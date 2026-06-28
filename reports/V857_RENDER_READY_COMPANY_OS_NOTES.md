# V857 Render Ready Company OS Notes

## Build
- `tools/build_clean_release.py` actualizado para incluir reportes V857 y auditoría ZIP V857.
- El ZIP final debe generarse desde la carpeta oficial, no desde ZIP viejo.

## Seguridad
- No se exponen secrets.
- Company OS no lee ni imprime API keys.
- No se llama Render real desde esta versión.
- No se afirma deploy real.

## Validación requerida
- `py_compile`.
- `compileall`.
- Jinja parse.
- `check_madrid_times`.
- Checks V855, V856 y V857.
- Smoke Flask.
- `audit_release_zip` con `forbidden_count=0`.
