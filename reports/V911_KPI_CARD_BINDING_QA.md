# V911 KPI Card Binding QA

Version: `V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL`

## Problem

El video mostraba KPIs pegados:

- `Capturas0desktop/mobile`
- `Comparaciones18reference_images`
- `Gaps resueltos0por captura`
- `Gaps pendientes18requieren browser real`
- `Runner localListoPowerShell / bat / sh`

## Fix

Se introdujo contrato visual V911:

- `.v911-admin-kpi-grid`
- `.v911-kpi-card`
- `.v911-kpi-label`
- `.v911-kpi-value`
- `.v911-kpi-hint`

Tambien se reforzo `templates/partials/ui_components.html` para que las macros principales de metricas emitan label/value/hint separables.

## Screens touched

- `/admin/autonomous-company-sentinel`
- `/admin/sentinel-codex-outbox`
- `/admin/sentinel-issues`

## Result

Los KPIs quedan estructurados como etiqueta, valor y ayuda, evitando texto concatenado.
