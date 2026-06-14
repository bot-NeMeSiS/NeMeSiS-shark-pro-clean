# V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP

## Objetivo
Auditoría completa sobre el ZIP real subido por el usuario, usando V780 como base detectada, para estabilizar la app antes de dejarla sin tocar un tiempo.

## Hallazgos reales de auditoría
- El ZIP completo recibido incluía material de desarrollo que no debe subirse como release: `.git`, `.venv` y `release_output` con ZIPs antiguos. La salida Render Ready limpia los excluye.
- Había una ruta duplicada: `/admin/launch-certification` registrada en dos pantallas admin distintas.
- Varios checks antiguos V774-V778 estaban obsoletos frente a la estructura actual V780/V781 y fallaban aunque la app tuviera la capa activa.
- Varias pantallas admin imprimían `created_at`, `sent_at`, `finished_at`, `started_at` o `last_login` sin filtro Madrid.
- Se detectó un enlace roto en observabilidad admin: `/admin/observability/errorserror_id=...`.

## Correcciones aplicadas
- Versión elevada a `V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP`.
- `APP_VERSION` actualizado.
- `/admin/launch-certification` queda para certificación final; Go Live conserva alias propio `/admin/go-live-certification`.
- Timestamps genéricos en plantillas admin pasan por `madrid_datetime_label`.
- Se corrige el enlace de detalle en `admin_observability_errors.html`.
- Checks V771-V780 actualizados para aceptar V781 como evolución compatible.
- Añadido `tools/check_v781_full_app_audit_stability.py`.
- `tools/build_clean_release.py` actualizado para incluir reportes y auditorías V779/V780/V781.

## No tocado
- `DB_PATH`.
- Usuarios, sesiones y membresías.
- Telegram automático y manual.
- `AUTOMATION_SECRET`.
- Cron Telegram y runner Render.
- Picks, grading y Track Record.
- Highlights.
- Data Marketplace y Automation Center.
- Madrid Time engine.
- Capa V779 de escudos/banderas.
- Reparación V780 de directo/live.

## Resultado
V781 es una versión de limpieza, auditoría y estabilidad: no añade una nueva interfaz masiva, sino que corrige problemas de consistencia, checks, rutas duplicadas, timestamps Madrid y empaquetado limpio.
