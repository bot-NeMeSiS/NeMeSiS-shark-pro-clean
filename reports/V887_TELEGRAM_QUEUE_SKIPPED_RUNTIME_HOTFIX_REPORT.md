# V887 Telegram Queue Skipped Runtime Hotfix Report

## Versión

`V887_TELEGRAM_QUEUE_SKIPPED_RUNTIME_HOTFIX_FINAL`

## Objetivo

Corregir el error real de runtime:

`name 'QUEUE_SKIPPED' is not defined`

sin tocar secretos, sin enviar Telegram real, sin inventar datos y sin alterar la lógica premium de no filler/dedupe.

## Cambios aplicados

- `app.py`
  - `APP_VERSION` actualizado a V887.
  - `QUEUE_SKIPPED` importado desde `engines.telegram_delivery_engine`.
  - `/api/runtime-version` añade `has_v887_telegram_queue_skipped_hotfix`.

- `VERSION.txt`
  - actualizado a V887.

- `APP_VERSION`
  - actualizado a V887.

- `templates/base.html`
  - meta version V887.
  - cache CSS V887.
  - `data-v887-shell="true"`.
  - comentario activo V887.

- `tools/check_v887_telegram_queue_skipped_hotfix.py`
  - nuevo check específico de hotfix.

## Qué se preserva

- V818 master tick.
- Protección `AUTOMATION_SECRET`.
- Madrid Time.
- Telegram no filler/dedupe.
- V844 Telegram premium.
- V862 Continuous Sentinel.
- V865 Sentinel Workflow.
- V886 browser/nav QA.
- DB_PATH.
- usuarios, sesiones, membresías y pagos.

## Qué no se tocó

- No se tocaron secretos.
- No se expuso `TELEGRAM_BOT_TOKEN`.
- No se expuso `AUTOMATION_SECRET`.
- No se envió Telegram real.
- No se inventaron picks.
- No se inventaron partidos.
- No se tocaron pagos.
- No se borró DB ni usuarios.
- No se hizo push ni deploy automático.

## Resultado esperado

El endpoint `/api/automation/telegram/tick` puede omitir elementos de cola con estado `skipped` sin lanzar `NameError`.

## Validación local final

- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines tools`: OK.
- `python tools/check_madrid_times.py`: OK.
- `python tools/check_v887_telegram_queue_skipped_hotfix.py`: OK.
- Parseo Jinja con entorno Flask real: 161 templates OK.
- Smoke Flask local: 29 rutas OK.
- Cron Telegram sin secret: 403.
- Cron Telegram con secret local y runner Render: 200.
- Master tick sin secret: 403.
- Health-check con secret local: 200.
- Continuous Sentinel: score 10.0, 0 issues, 0 críticos.
- `build_clean_release`: OK.
- `audit_release_zip`: `forbidden_count=0`, `missing_required_root=[]`.

## Nota de compatibilidad

El check V886 antiguo es rígido por versión y espera `VERSION.txt` en V886. Tras el bump correcto a V887, ese check falla por contrato de versión antigua, no por regresión funcional de navegación.
