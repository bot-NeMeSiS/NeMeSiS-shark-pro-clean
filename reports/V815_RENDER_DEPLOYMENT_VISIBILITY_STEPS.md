# V815 Render Deployment Visibility Steps

## ZIP final

`NeMeSiS_SHARK_PRO_V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL_RENDER_READY.zip`

## Pasos Render

1. Subir/desplegar el ZIP final.
2. Usar `Clear build cache & deploy`.
3. Esperar a que el worker arranque.
4. Abrir `/api/runtime-version`.
5. Confirmar:
   - `app_version = V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`
   - `version_txt = V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`
   - `has_v815_shell = true`
   - `has_v815_css = true`
   - `static_css_cache_busting = true`

## Comprobacion fuente

Abrir `/app`, ver codigo fuente y buscar:

- `NEMESIS V815 CLIENT SHELL ACTIVE`
- `data-v815-shell="true"`
- `app.css?v=V815_RENDER_VISIBLE_REFERENCE_REBUILD_REPO_RECONCILIATION_FINAL`

## Si visualmente sigue viejo

- Si `/api/runtime-version` no muestra V815: Render sirve otra version.
- Si runtime muestra V815 pero fuente no: se abre otra URL/servicio.
- Si fuente muestra V815 pero visual no: cache de navegador/CDN.
- Si ZIP aparece anidado: reconstruir/subir el ZIP correcto.
