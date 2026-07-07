# Codex Outbox - V906 Browser QA Findings

## ACTIVE_FIX_PROMPTS

Sin prompts activos reproducibles.

## VISUAL_REFERENCE_PROMPTS

Archivado por V906: usar SCREENSHOT_BASED_VISUAL_PROMPTS cuando existan capturas reales.

## FUNCTIONAL_PROMPTS

Sin prompts funcionales activos.

## ADMIN_PROMPTS

Sin prompts admin activos sin captura.

## TELEGRAM_PROMPTS

Sin prompts Telegram activos; no enviar Telegram real.

## ARCHIVED_OBSOLETE_PROMPTS

Prompts estáticos previos archivados hasta evidencia reproducible.

## FALSE_POSITIVE_PROMPTS

Sin falsos positivos pendientes.

## V904_REFERENCE_GAPS_WORKFORCE_STATUS

- mode: reference_scan
- gaps_read: 14
- gaps_addressed: 8
- gaps_pending: 6
- prompts_active: 0
- deploy_status: pending_runtime_confirmation
- secret_masking_status: masked_configured_missing_only
- next_step: Ejecutar Browser QA real antes de declarar pixel-perfect.

### action_policy

- SAFE_AUTOFIX: 0
- CODEX_PROMPT_REQUIRED: 0
- HUMAN_APPROVAL_REQUIRED: 0

### dangerous_requires_approval

Pagos, secretos, Telegram real, DB, usuarios, sesiones, deploy, push y llamadas caras quedan fuera del autofix automatico.

## V905_FINAL_REFERENCE_GAPS_BROWSER_QA_STATUS

- archived_by_v906: true
- pixel_perfect_claim: false
- pending_browser_qa: preserved for compatibility; V906 owns current screenshot prompts.

## V906_BROWSER_QA_FINDINGS

- browser_qa_status: BROWSER_QA_UNAVAILABLE
- screenshots_captured: 0
- reference_comparisons: 14
- visual_gaps_resolved: 0
- visual_gaps_pending: 14
- pixel_perfect_claim: false

## SCREENSHOT_BASED_VISUAL_PROMPTS

Sin capturas reales porque Playwright no está disponible. Se generan prompts pendientes de captura, no cierre visual.

## ADMIN_VISUAL_PROMPTS

### /admin-login

- ruta: `/admin-login`
- captura actual: `pendiente`
- referencia usada: `reference_images/admin/reference_import_v900_01.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /admin/autonomous-company-sentinel

- ruta: `/admin/autonomous-company-sentinel`
- captura actual: `pendiente`
- referencia usada: `reference_images/admin/reference_import_v900_01.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /admin/dashboard

- ruta: `/admin/dashboard`
- captura actual: `pendiente`
- referencia usada: `reference_images/admin/reference_import_v900_01.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /admin/not-found-events

- ruta: `/admin/not-found-events`
- captura actual: `pendiente`
- referencia usada: `reference_images/admin/reference_import_v900_01.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /admin/sentinel-codex-outbox

- ruta: `/admin/sentinel-codex-outbox`
- captura actual: `pendiente`
- referencia usada: `reference_images/admin/reference_import_v900_01.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /admin/sentinel-issues

- ruta: `/admin/sentinel-issues`
- captura actual: `pendiente`
- referencia usada: `reference_images/admin/reference_import_v900_01.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.


## CLIENT_MOBILE_PROMPTS

### /

- ruta: `/`
- captura actual: `pendiente`
- referencia usada: `reference_images/client/reference_import_v900_08.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /app

- ruta: `/app`
- captura actual: `pendiente`
- referencia usada: `reference_images/client/reference_import_v900_08.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /profile

- ruta: `/profile`
- captura actual: `pendiente`
- referencia usada: `reference_images/profile/reference_import_v900_15.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.


## PICKS_LIVE_CALENDAR_PROMPTS

### /calendar

- ruta: `/calendar`
- captura actual: `pendiente`
- referencia usada: `reference_images/calendar/reference_import_v900_10.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /live

- ruta: `/live`
- captura actual: `pendiente`
- referencia usada: `reference_images/live/reference_import_v900_09.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /picks

- ruta: `/picks`
- captura actual: `pendiente`
- referencia usada: `reference_images/picks/reference_import_v900_11.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.


## SHARK_TELEGRAM_PROMPTS

### /shark

- ruta: `/shark`
- captura actual: `pendiente`
- referencia usada: `reference_images/shark/reference_import_v900_12.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.

### /telegram

- ruta: `/telegram`
- captura actual: `pendiente`
- referencia usada: `reference_images/telegram/reference_import_v900_16.png`
- gap observado: Captura real pendiente.
- objetivo visual: comparar captura real contra referencia y corregir solo diferencias visibles reales.
- archivos probables: templates, static/app.css, partials UI.
- restricciones: no inventar datos, no tocar secretos, no mezclar admin/cliente, no declarar pixel-perfect sin capturas.
- validaciones: check V906, Sentinel, smoke Flask, Browser QA cuando Playwright esté disponible.


## PENDING_HUMAN_REVIEW

Sin prompts activos en esta sección.

## ARCHIVED_STATIC_PROMPTS

Prompts estáticos previos quedan archivados hasta que exista captura real o evidencia reproducible.
