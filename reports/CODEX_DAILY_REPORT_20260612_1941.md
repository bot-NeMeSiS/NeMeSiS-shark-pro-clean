# Codex Daily Automation

Versión: `V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX`

Generado: `2026-06-12T19:41:10+02:00`

## Limpieza

- Archivos: 4817
- Basura segura: 4246
- Peligrosos: 0
- Revisar manualmente: 307

## ZIP

- Disponible: True
- OK: True
- Archivo: NeMeSiS_SHARK_PRO_V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX_RENDER_READY.zip
- Fuera del proyecto: False
- ZIPs en raíz del proyecto: []

## Hora Madrid

- Engine: engines/madrid_time_engine.py
- Selftest: True

## Módulos activos

{
  "telegram_football_only": true,
  "pro_calibration": true,
  "picks_quality": true,
  "shark_advisor": true,
  "team_identity": true,
  "data_memory": true,
  "visual_pro": true,
  "release_cleaner": true
}

## Memoria SHARK

- Engine: True
- Admin: True
- Recomendación: Data Memory está preparado; revisar admin/data-memory tras Daily Run real.

## Recomendaciones

- Ejecutar python tools/purge_project_safe.py --dry-run y luego --apply si todo es seguro.
- Validar compileall, smoke_check, Cron 403/200 y runtime-version antes de cada entrega.

## Prompt actual

```text
Estoy continuando NeMeSiS SHARK PRO desde la versión V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX.

Reglas:
- No rehacer la app.
- No romper Render, Telegram automático, Cron, DB_PATH=/data/database.db, AUTOMATION_SECRET, login, admin, cliente, membresías, SHARK, picks, combis hasta 15 ni Data Memory.
- No tocar ni mostrar secrets reales.
- Entregar siempre ZIP limpio Render Ready.

Estado:
- Archivos totales: 4817
- Basura segura detectada: 4246
- Peligrosos detectados: 0
- ZIP: NeMeSiS_SHARK_PRO_V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX_RENDER_READY.zip | OK: True | fuera del proyecto: False
- ZIPs en raiz del proyecto: []
- Hora Madrid: Europe/Madrid | selftest: True
- Modulos activos: Telegram football-only, calibracion PRO, calidad picks, SHARK Advisor, Team Identity, Data Memory, Visual PRO y Release Cleaner.
- Data Memory engine: True | admin: True
- Render/Cron: no mostrar secrets; validar 403 sin secret y 200 con secret en tick/daily.
- Telegram: revisar ultimo tick/daily, enviados hoy, descartados y errores desde admin diagnostics.

Próximos objetivos recomendados:
- Ejecutar python tools/purge_project_safe.py --dry-run y luego --apply si todo es seguro.
- Validar compileall, smoke_check, Cron 403/200 y runtime-version antes de cada entrega.

Validación obligatoria:
- python -m py_compile app.py
- python -m compileall -q .
- python tools/check_madrid_times.py
- python tools/nemesis_daily_codex.py
- python tools/smoke_check.py
- python tools/build_clean_release.py
- python tools/audit_release_zip.py
- python tools/validate_release.py
- pytest -q si pytest está instalado

```
