# V851 Production Stability QA

## Alcance
V851 es una corrección de marca/header y texto visible. No toca:
- DB_PATH.
- Usuarios, sesiones, membresías ni pagos.
- API-SPORTS/API-Football.
- The Odds API.
- Telegram V844.
- SHARK V845.
- Live/escudos V850.
- Master tick V818.

## Validaciones planificadas
- `python -m py_compile app.py`
- `python -m compileall app.py engines tools`
- Parse Jinja templates.
- `tools/check_madrid_times.py`
- Checks V851.
- Smoke Flask de rutas principales y cron 403/200.
- ZIP limpio con `forbidden_count=0`.

## Resultado ejecutado
- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines tools`: OK.
- Parse Jinja templates: OK.
- `tools/check_madrid_times.py`: OK.
- Checks V851: OK.
- Checks de regresión V850/API-SPORTS/SHARK/Telegram: OK.
- Smoke Flask: OK con `DB_PATH` temporal local, porque `/data` es ruta de Render y no existe en Windows local.
- Master tick sin secret: 403.
- Master tick con secret temporal y `dry_run=1`: 200.
- Health-check con secret temporal: 200.
- ZIP: `forbidden_count=0`.

## ZIP final
`release_output/NeMeSiS_SHARK_PRO_V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX_RENDER_READY.zip`
