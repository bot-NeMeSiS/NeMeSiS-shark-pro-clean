# V873 real production visual logos SHARK header final

## Base

- Producción real: V871.
- Local inicial: V872.
- Local final: V873.

## Corregido

- Versionado V873 en `VERSION.txt`, `APP_VERSION`, `app.py`, `base.html` y cache CSS.
- Runtime flag `has_v873_real_production_visual_logos_shark_header`.
- Saneado en origen de errores API-SPORTS mediante `sanitize_provider_error()`.
- Runtime `last_error_state` para distinguir error histórico saneado de error activo.
- Estados explícitos para OpenAI/SHARK sin tocar secretos.
- Estados explícitos para cache de logos a cero.
- Fallback visual de escudos/logos reforzado.
- Reportes y checks V873.

## Probado en real

- Runtime Render V871 consultado.

## Probado local

- `py_compile app.py`: OK.
- `compileall app.py engines tools`: OK.
- `check_madrid_times.py`: OK.
- Checks V862, V863, V865, V866, V867, V868, V869, V870, V871, V872, V873: OK.
- Parse Flask Jinja: 160 templates OK.
- Smoke local cliente/admin/API: OK.
- Master tick sin secret: 403.
- Master tick con secret dry-run: 200.
- Health-check con secret: 200.
- Continuous Sentinel static: score 10.0, 0 issues.

## No probado

- Render V873 desplegado.
- Capturas reales V873.
- Telegram real.
- Pagos reales.
- APIs externas caras.
