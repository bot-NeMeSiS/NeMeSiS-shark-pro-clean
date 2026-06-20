# V841 Production Stability QA

Estado: validado.

- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines tools`: OK.
- Parse Jinja de 151 templates: OK.
- `tools/check_madrid_times.py`: OK.
- Checks V841: OK.
- Smoke Flask: OK, sin 500 ni "Incidencia controlada" en rutas revisadas.
- `/api/automation/master-tick` sin secret: 403.
- `/api/automation/master-tick` con secret y `dry_run=1`: 200.
- `/api/automation/health-check` con secret: 200.
- `/api/runtime-version`: 200 con V841 y compatibilidad V818-V840.

Nota: las rutas privadas sin sesión redirigen con 302, comportamiento esperado.
