# V863 Real Performance QA

## Evidencia real

Las rutas públicas probadas en Render respondieron sin 500. El runtime expone:

- `static_app_css_size`: 830465 bytes en producción V862.
- `usage_guard.no_page_render_calls`: `true`.
- `usage_guard.cache_first`: `true`.

## Pendiente

No se hizo benchmark profundo ni Lighthouse. Queda pendiente medir TTFB, peso HTML y rutas lentas con navegador real.
