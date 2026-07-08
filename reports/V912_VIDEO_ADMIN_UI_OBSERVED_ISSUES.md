# V912 Video Admin UI Observed Issues

Version objetivo: `V912_VIDEO_ADMIN_UI_COPY_POLISH_BROWSER_QA_QUEUE_FINAL`

Base local usada: V911 avanzada con correcciones `V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL`, integrada en V912 para no mantener un conflicto de nombre.

Estado Render real consultado antes de V912: `V907_BROWSER_QA_ENABLEMENT_FIRST_SCREENSHOT_GAP_FIX_FINAL`.

## Evidencia del video

El archivo de video no estuvo disponible dentro del workspace en esta pasada. Se usa como evidencia textual lo reportado por el usuario:

- Texto ambiguo tipo `Salir cliente` dentro de admin.
- Navegación cliente/admin mezclada.
- KPI cards con textos visualmente pegados.
- Paneles admin con layout poco ordenado.
- Browser QA / Visual Queue poco claro.
- Local/Render status confuso.

## Correcciones V912

- Admin rail queda con `Vista pública` y `Cerrar sesión admin`.
- `base.html` refuerza `is_admin_surface` para `/admin-login`, `/admin/*` y `/api/admin/*`.
- Admin no renderiza sidebar cliente, bottom nav cliente ni SHARK flotante cliente.
- KPI cards usan `label`, `value` y `hint` separados mediante clases V912.
- Browser QA / Visual Queue explica que no hay pixel-perfect sin capturas reales.
- Runtime/admin separa “Runtime actual de esta app” de “Render externo no consultado en esta vista”.

## Limitación

No se declara pixel-perfect porque Playwright sigue no disponible en este entorno y no hay screenshots reales.
