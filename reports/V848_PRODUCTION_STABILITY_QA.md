# V848 Production Stability QA

Validaciones objetivo:

- `py_compile app.py`.
- `compileall app.py engines tools`.
- Parse Jinja.
- Madrid Time.
- Checks V847 compatibles.
- Checks V848.
- Smoke Flask sin 500/502.
- Cron master tick 403 sin secret y 200 con secret dry-run.
- Health-check 200 con secret.
- ZIP `forbidden_count=0`.

Resultado final:

- `py_compile app.py`: OK.
- `compileall app.py engines tools`: OK.
- Parse Jinja de 145 templates: OK.
- Madrid Time: OK.
- Checks V848: OK.
- Compatibilidad V847/V845/V844/V818: OK.
- Smoke Flask: OK, sin 500/502.
- Master tick sin secret: 403.
- Master tick con secret y `dry_run=1`: 200.
- Health-check con secret: 200.
- `audit_release_zip`: OK, `forbidden_count=0`.
