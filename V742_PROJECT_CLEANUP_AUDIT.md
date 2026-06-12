# V742 Project Cleanup Audit

- Versión: `V742_TOP_APP_LIVE_DETAIL_TRACK_RECORD_MATCH_INTELLIGENCE_VIDEO_HIGHLIGHTS_FINAL`
- Archivos escaneados: 5081
- Candidatos locales excluidos del ZIP: 737
- Carpetas temporales/cache detectadas: 116
- Duplicados HTML en raíz: 0
- Duplicados Python peligrosos: 41

## Política de release
- El ZIP excluye `.git`, `.venv`, cachés, DB locales, logs, vídeos, capturas y ZIPs internos.
- No se borran `templates/`, `static/`, `engines/`, `tools/`, `tests/`, `blueprints/` ni `services/`.
- No se tocan secrets ni `DB_PATH`.

## Muestra de candidatos excluidos
- `data/telegram_reliability_audit.db`
- `release_output/NeMeSiS_SHARK_PRO_V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX_RENDER_READY.zip`
- `release_output/NeMeSiS_SHARK_PRO_V726_TOTAL_PROJECT_CLEANUP_LIVE_EXPERIENCE_ORGANIZATION_RENDER_READY.zip`
- `release_output/NeMeSiS_SHARK_PRO_V727_TELEGRAM_RELIABILITY_COMMAND_CENTER_RENDER_READY.zip`
- `release_output/NeMeSiS_SHARK_PRO_V742_SALE_READY_LIVE_DETAIL_TRACK_RECORD_TELEGRAM_FINAL_POLISH_RENDER_READY.zip`
- `__pycache__/app.cpython-312.pyc`
- `__pycache__/database_manager.cpython-312.pyc`
- `.venv/Lib/site-packages/blinker/__pycache__/base.cpython-312.pyc`
- `.venv/Lib/site-packages/blinker/__pycache__/_utilities.cpython-312.pyc`
- `.venv/Lib/site-packages/blinker/__pycache__/__init__.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/core.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/decorators.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/exceptions.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/formatting.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/globals.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/parser.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/shell_completion.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/termui.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/testing.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/types.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/utils.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/_compat.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/_termui_impl.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/_textwrap.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/_winconsole.cpython-312.pyc`
- `.venv/Lib/site-packages/click/__pycache__/__init__.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/__pycache__/ansi.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/__pycache__/ansitowin32.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/__pycache__/initialise.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/__pycache__/win32.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/__pycache__/winterm.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/__pycache__/__init__.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/ansitowin32_test.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/ansi_test.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/initialise_test.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/isatty_test.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/utils.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/winterm_test.cpython-312.pyc`
- `.venv/Lib/site-packages/colorama/tests/__pycache__/__init__.cpython-312.pyc`
- `.venv/Lib/site-packages/flask/__pycache__/app.cpython-312.pyc`

## Revisión manual
- Revisar Python duplicado en raíz frente a engines/tools.
- Revisar elementos top-level no estándar antes de borrarlos.
