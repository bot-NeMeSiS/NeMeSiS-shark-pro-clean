# V816 Render Deployment Steps

## ZIP correcto

`NeMeSiS_SHARK_PRO_V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL_RENDER_READY.zip`

## Pasos

1. Subir/desplegar el ZIP final.
2. Usar `Clear build cache & deploy`.
3. Abrir `/api/runtime-version`.
4. Confirmar:
   - `app_version = V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL`
   - `version_txt = V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL`
   - `has_v816_shell = true`
   - `has_v816_css = true`
   - `static_css_cache_busting = true`
5. Abrir codigo fuente de `/app` y buscar:
   - `NEMESIS V816 LIVE REFERENCE VISUAL DIFF ACTIVE`
   - `data-v816-shell="true"`
   - `app.css?v=V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL`

## Si sigue viejo

- Runtime no muestra V816: Render sirve otro ZIP/app.
- Runtime muestra V816 pero fuente no: URL/servicio incorrecto.
- Fuente muestra V816 pero visual no cambia: cache navegador/CDN.
- ZIP anidado: reconstruir y subir el ZIP limpio.
