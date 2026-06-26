# V847 Production Stability QA

Puntos protegidos:

- DB_PATH no se modifica.
- Telegram V844 no se modifica.
- SHARK V845 se conserva y solo recibe contexto adicional.
- V818 master tick y health-check se conservan.
- API-SPORTS no se llama desde cada render.
- No se exponen secrets en runtime/admin.
- Fallback a cache/datos existentes si proveedor falla.

Validaciones ejecutadas:

- `py_compile app.py`: OK.
- `compileall app.py engines tools`: OK.
- Parse Jinja de 145 templates: OK.
- `tools/check_madrid_times.py`: OK.
- Suite V847: OK.
- Smoke Flask: OK, sin 500/502.
- Master tick sin secret: 403.
- Master tick con secret y `dry_run=1`: 200.
- Health-check con secret: 200.
- `audit_release_zip`: OK, `forbidden_count=0`.

Ver también `RELEASE_MANIFEST_V847.json`.
