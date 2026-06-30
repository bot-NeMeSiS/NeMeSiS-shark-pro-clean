# Daily Render Runtime 2026-06-30

## Estado local
- Runtime local probado con `.venv\Scripts\python.exe`.
- `/api/runtime-version` respondió 200.
- `app_version`: `V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL`.
- `app_py_path`: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro\app.py`.
- `db_path` usado en prueba: temporal local `nemesis_v865_workflow.sqlite`.

## Flags observados
- `api_sports_configured`: false.
- `api_football_configured`: false.
- `telegram_configured`: false.
- `openai_configured`: false.
- `the_odds_configured`: false.
- `automation_secret_configured`: false.
- `api_sports_credit_guard_enabled`: true.
- `crest_engine_loaded`: true.

## Render real
- No probado en Render real.
- No se consultaron logs reales.
- No se hizo deploy.
- No se hizo push.

## Riesgo
- Bloqueo de certificación real: faltan credenciales/entorno Render y autorización para pruebas productivas.
- Acción segura sugerida: comparar este V865 ZIP con Render antes de deploy y ejecutar smoke real con `AUTOMATION_SECRET` controlado.
