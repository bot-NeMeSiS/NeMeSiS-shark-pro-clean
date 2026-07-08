# V912 Browser QA / Visual Queue Panel QA

## Estado real

Browser QA sigue preparado, pero no disponible en este entorno:

- Playwright no instalado.
- Capturas reales: 0.
- Pixel-perfect: no permitido.
- Visual queue: bloqueada por falta de screenshot.

## Corrección

Los paneles admin ahora explican:

- Browser QA disponible/no disponible.
- Capturas realizadas.
- Comparaciones contra `reference_images`.
- Gaps pendientes.
- Estado de la cola visual.
- `No pixel-perfect sin capturas reales`.

## Archivos tocados

- `templates/admin_autonomous_company_sentinel.html`
- `templates/admin_sentinel_codex_outbox.html`
- `static/app.css`
- `data/runtime/autonomous_company_sentinel/visual_fix_queue.json`
- `data/runtime/autonomous_company_sentinel/browser_qa_status.json`

## Pendiente

Instalar Playwright en un entorno autorizado y ejecutar Browser QA real.
