# V725 Madrid Time + Release Workflow Automation Fix

## Objetivo

Corregir la diferencia real de horarios donde partidos que debían verse a las 21:00 en España podían aparecer como 19:00 en algunas pantallas, y reforzar el flujo de release para que los ZIP Render Ready no queden dentro de la carpeta de la aplicación.

## Causa raíz

La aplicación ya tenía helpers de localización española, pero había dos problemas:

- Algunas fechas API con `Z`, `+00:00` o sin zona horaria no pasaban siempre por una conversión centralizada Europe/Madrid.
- Varias plantillas seguían priorizando campos crudos como `kickoff_time`, `match_time` o `kickoff_iso` antes que campos seguros de visualización.

Esto permitía que una hora UTC real como `2026-06-12T19:00:00Z` se mostrara como `19:00` en vez de `21:00` en horario de verano español.

## Corrección aplicada

- Creado `engines/madrid_time_engine.py` como motor central de hora Madrid.
- Conectado `engines/spanish_localization_engine.py` al nuevo motor.
- Añadidos campos seguros en partidos y picks: `madrid_time`, `madrid_date`, `madrid_date_label`, `madrid_display`, `safe_time`, `display_datetime`.
- Endurecido Telegram para usar siempre visualización Madrid antes de generar mensajes.
- Añadido `/admin/time-diagnostics` protegido para revisar conversiones reales.
- Añadida herramienta `tools/check_madrid_times.py`.
- Actualizada versión a `V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX`.

## Pruebas horarias obligatorias

- `2026-06-12T19:00:00Z` -> `21:00` Europe/Madrid.
- `2026-12-12T20:00:00Z` -> `21:00` Europe/Madrid.

## Pantallas protegidas

- Home
- Dashboard / Sports Hub
- Live
- Calendar
- Picks
- Combis
- Favoritos
- Match Hub
- Match Detail
- Team Detail
- SHARK
- Telegram
- Paneles admin con datos de partidos

## Release workflow

- `tools/build_clean_release.py` intenta generar el ZIP en `../releases`.
- Si el entorno no permite escribir fuera, usa `release_output/`, carpeta excluida del ZIP.
- El auditor falla si encuentra cualquier ZIP interno.
- `tools/validate_release.py` busca el ZIP en `../releases`, luego `release_output/`, luego raíz como compatibilidad.

## Seguridad

No se tocaron secretos reales, variables Render reales ni configuración Cron real.

## Validación ejecutada

- `python -m py_compile app.py`: OK.
- `python -m compileall -q app.py engines database_manager.py services tools`: OK.
- `python tools/check_madrid_times.py`: OK.
- `python tools/nemesis_daily_codex.py`: OK.
- `python tools/smoke_check.py`: OK con avisos históricos de endpoints V601/V602 no presentes.
- Flask test client con DB temporal: `/`, `/dashboard`, `/sports-hub`, `/live`, `/calendar`, `/picks`, `/combis`, `/telegram`, `/shark`, `/favorites`, `/perfil`, `/membership`, `/admin/time-diagnostics`, `/admin/codex-automation`, `/api/runtime-version`, `/api/timezone-check`, Cron 403/200: sin 500.
- `python tools/build_clean_release.py`: OK.
- `python tools/audit_release_zip.py`: OK, 0 prohibidos.
- `python tools/validate_release.py`: OK hasta auditoría ZIP; se detiene porque `pytest` no está instalado.
- Prueba artificial de ZIP interno: el auditor devuelve `ok=False` y razón `zip interno`.

## ZIP final

El entorno local no permitió escribir en `../releases`, así que se usó el fallback previsto:

`release_output/NeMeSiS_SHARK_PRO_V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX_RENDER_READY.zip`

La carpeta `release_output/` está excluida del ZIP. El ZIP contiene 254 archivos, 0 ZIPs internos y 0 carpetas prohibidas.
