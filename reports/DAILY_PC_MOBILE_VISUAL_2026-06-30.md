# Daily PC Mobile Visual 2026-06-30

## Revisado
- `templates/base.html`.
- `templates/admin_sentinel_workflow.html`.
- `static/app.css` por marcadores V864/V865 existentes.
- Navegación admin.

## Corregido
- Añadido acceso directo admin a `/admin/sentinel-workflow` con etiqueta `Workflow`.
- Impacto: V865 deja de estar solo como ruta oculta/API y queda operable desde el command center admin.

## Probado local
- Rutas públicas/locales con test client:
  - `/`: 200.
  - `/app`: 302.
  - `/partidos`: 200.
  - `/live`: 200.
  - `/picks`: 200.
  - `/shark`: 200.
  - `/telegram`: 302.
  - `/track-record`: 200.
  - `/admin/dashboard`: 302 sin sesión.
  - `/admin/sentinel-workflow`: 302 sin sesión.

## No probado
- Browser real desktop/mobile.
- Capturas 390px, 430px, 768px.
- Render real.

## Pendiente visual
- Revisar las rutas señaladas por Sentinel para confirmar si `None/null/undefined` aparece realmente visible.
