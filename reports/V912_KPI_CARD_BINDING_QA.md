# V912 KPI Card Binding QA

## Problema observado

El video mostraba KPIs visualmente concatenados, por ejemplo:

- `Capturas0desktop/mobile`
- `Comparaciones18reference_images`
- `Gaps pendientes18requieren browser real`
- `Runner localListoPowerShell / bat / sh`

## Corrección

Se estandarizó el patrón:

- `v912-kpi-label`
- `v912-kpi-value`
- `v912-kpi-hint`

Aplicado en:

- `templates/partials/ui_components.html`
- `templates/admin_autonomous_company_sentinel.html`
- `templates/admin_sentinel_codex_outbox.html`
- `templates/admin_sentinel_issues.html`
- `static/app.css`

## Validación

`tools/check_v912_video_admin_ui_copy_polish.py` valida que `/admin/autonomous-company-sentinel` no contiene los tokens concatenados reportados.
