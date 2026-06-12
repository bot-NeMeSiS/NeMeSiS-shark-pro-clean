# Codex Daily Automation

Versión: `V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM`

Generado: `2026-06-12T15:56:29+02:00`

## Limpieza

- Archivos: 4662
- Basura segura: 4108
- Peligrosos: 0
- Revisar manualmente: 301

## ZIP

- Disponible: True
- OK: True
- Archivo: NeMeSiS_SHARK_PRO_V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM_RENDER_READY.zip

## Memoria SHARK

- Engine: True
- Admin: True
- Recomendación: Data Memory está preparado; revisar admin/data-memory tras Daily Run real.

## Recomendaciones

- Ejecutar python tools/purge_project_safe.py --dry-run y luego --apply si todo es seguro.
- Validar compileall, smoke_check, Cron 403/200 y runtime-version antes de cada entrega.

## Prompt actual

```text
Estoy continuando NeMeSiS SHARK PRO desde la versión V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM.

Reglas:
- No rehacer la app.
- No romper Render, Telegram automático, Cron, DB_PATH=/data/database.db, AUTOMATION_SECRET, login, admin, cliente, membresías, SHARK, picks, combis hasta 15 ni Data Memory.
- No tocar ni mostrar secrets reales.
- Entregar siempre ZIP limpio Render Ready.

Estado:
- Archivos totales: 4662
- Basura segura detectada: 4108
- Peligrosos detectados: 0
- ZIP: NeMeSiS_SHARK_PRO_V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM_RENDER_READY.zip | OK: True
- Data Memory engine: True | admin: True

Próximos objetivos recomendados:
- Ejecutar python tools/purge_project_safe.py --dry-run y luego --apply si todo es seguro.
- Validar compileall, smoke_check, Cron 403/200 y runtime-version antes de cada entrega.

Validación obligatoria:
- python -m py_compile app.py
- python -m compileall -q .
- python tools/smoke_check.py
- python tools/build_clean_release.py
- python tools/audit_release_zip.py
- python tools/validate_release.py
- pytest -q si pytest está instalado

```
