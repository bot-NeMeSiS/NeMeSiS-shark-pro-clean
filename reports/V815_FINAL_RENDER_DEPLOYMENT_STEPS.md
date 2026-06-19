# V815 Final Render Deployment Steps

## ZIP a subir

`NeMeSiS_SHARK_PRO_V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED_RENDER_READY.zip`

## Comprobacion tras desplegar

1. Abrir:
   `/api/runtime-version`
2. Confirmar:
   - `app_version`: `V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`
   - `version_txt`: `V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`
   - `has_v815_shell`: `true`
   - `static_css_cache_busting`: `true`
3. Abrir `/app`.
4. Ver codigo fuente y buscar:
   - `NEMESIS V815 CLIENT SHELL ACTIVE`
   - `data-v815-shell="true"`
   - `app.css?v=V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`

## Clear build cache

En Render:

1. Abrir el servicio.
2. Ir a `Manual Deploy`.
3. Usar `Clear build cache & deploy`.
4. Esperar a que el deploy termine.

## Cache navegador

Si el runtime marca V815 pero visualmente se ve viejo:

1. Abrir en incognito.
2. Hacer hard refresh.
3. Borrar cache del navegador.
4. Confirmar que `app.css` carga con `?v=V815...`.

## Si todavia se ve V814/V812/V805

1. `/api/runtime-version` muestra version antigua: Render no esta ejecutando este ZIP.
2. `/api/runtime-version` muestra V815 pero el HTML fuente no: hay ruta o servicio incorrecto.
3. HTML fuente muestra V815 pero CSS no cambia: cache navegador/CDN.
4. ZIP tiene `app.py` dentro de carpeta anidada: subir ZIP reconstruido desde raiz.
