# V923 Browser QA Environment Decision

classification: PLAYWRIGHT_PACKAGE_MISSING
local_runner_available: true
github_action_available: true
playwright_available: false
browsers_available: false
can_capture: false
install_allowed: false

## Decisión
El entorno local puede ejecutar los scripts, pero no tiene Playwright instalado. La variable ENABLE_BROWSER_QA_INSTALL no está activa, así que no se instala automáticamente.

## Siguiente vía segura
- Ejecutar GitHub Action Browser QA.
- O activar instalación local autorizada y ejecutar Browser QA.
- O subir artifacts reales con capturas a reports/browser_qa_render/.

