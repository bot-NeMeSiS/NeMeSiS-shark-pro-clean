# V851 Assets, Favicon y PWA

## Assets revisados
- `static/img/shark-logo.svg`: existe y se mantiene como logo ligero.
- `templates/base.html`: referencia el SVG como favicon.
- `static/manifest.json`: no existe en esta base.

## Decisión
- No se añadieron imágenes pesadas.
- No se descargó ningún logo en runtime.
- No se modificaron rutas de escudos de equipos ni ligas.
- La solución de marca se resuelve con SVG existente + estructura HTML/CSS premium.

## Check
- `tools/check_v851_logo_assets_favicon_pwa.py`.
