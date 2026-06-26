# V853 Admin Text Orthography QA

Textos corregidos:

- `diagnsticos` -> `diagnósticos`.
- `Segn Render` -> `Según Render`.
- Separadores dobles en `Madrid  producción` normalizados a `Madrid · producción`.

Check añadido:
- `tools/check_v853_admin_text_orthography.py`

El check revisa plantillas admin clave y base para evitar mojibake y errores visibles específicos.
