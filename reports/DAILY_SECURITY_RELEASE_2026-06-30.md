# Daily Security Release 2026-06-30

## Seguridad
- API `/api/admin/sentinel-workflow/summary` devuelve 403 sin sesión admin.
- `/admin/sentinel-workflow` redirige a login sin sesión.
- No se tocaron secretos.
- No se tocaron pagos reales.
- No se borraron usuarios.
- No se borró DB.
- No se envió Telegram real.
- No se llamaron APIs externas reales.

## Checks ejecutados
- `py_compile`: OK.
- `compileall`: OK.
- `tools/check_v865_sentinel_issue_to_improvement_workflow.py`: OK.
- `tools/check_madrid_times.py`: OK.
- `tools/smoke_check.py` con `.venv`: OK con warnings existentes.
- `tools/run_continuous_sentinel_static.py` con `.venv`: OK, score 9.1.

## Warnings / bloqueos
- `python` no está en PATH; se usó `.venv\Scripts\python.exe` para checks con Flask y el Python embebido para checks sin Flask.
- `tools/check_v864_pc_mobile_visual_reference_big_leap.py` falla porque exige `VERSION.txt == V864`; con V865 activo no es check aplicable sin actualizar su matriz de versiones.
- Smoke warning: ruta duplicada `/admin/client-screens`.
- Smoke warning: endpoints legacy no encontrados `/api/v602/player-intelligence-check` y `/api/v601/api-exploitation-check`.

## Release
- `tools/build_clean_release.py` actualizado para incluir reportes `V865_`, `DAILY_` y auditoría ZIP V865.
