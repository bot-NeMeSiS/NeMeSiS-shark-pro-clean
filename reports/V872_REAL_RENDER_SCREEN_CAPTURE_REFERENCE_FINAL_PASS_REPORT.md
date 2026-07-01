# V872 real Render screen capture reference final pass

## Resumen

V872 convierte la revisión visual en una pasada honesta basada en runtime real y en checks locales. Render real está en V871, por tanto V872 queda listo como ZIP local para deploy manual.

## Corregido

- Versionado V872 en `VERSION.txt`, `APP_VERSION`, `app.py`, `base.html` y cache CSS.
- Flag runtime `has_v872_real_screen_capture_reference_pass`.
- Saneado local de `Invalid header value` para evitar exponer el valor crudo en runtime.
- CSS V872 acotado para overflow móvil, acciones compactas, empty states y admin sin elementos cliente.
- Release builder incluye reportes y auditoría ZIP V872.
- Checks de compatibilidad V862-V871 aceptan V872 como versión actual manteniendo sus garantías.

## Probado en real

- Runtime Render `/api/runtime-version`: producción en V871.

## Probado local

- `python -m py_compile app.py`: OK con `.venv`.
- `python -m compileall app.py engines tools`: OK con `.venv`.
- `python tools/check_madrid_times.py`: OK.
- Checks V862, V863, V865, V866, V867, V868, V869, V870, V871 y V872: OK.
- Parse Flask Jinja: 160 templates OK.
- Smoke local cliente/admin/API: OK con estados permitidos 200/302/401/403.
- Master tick sin secret: 403.
- Master tick con secret dry-run: 200.
- Health-check con secret: 200.
- Continuous Sentinel static: score 10.0, 0 issues.
- `build_clean_release`: ZIP V872 generado.
- `audit_release_zip`: `forbidden_count=0`, `missing_required_root=[]`.

## No probado

- Render V872 desplegado.
- Capturas nuevas con navegador por bloqueo de Playwright en el entorno.
- Telegram real.
- Pagos reales.
- APIs externas caras.
