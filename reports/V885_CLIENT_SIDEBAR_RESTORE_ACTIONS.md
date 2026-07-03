# V885 Client Sidebar Restore Actions

## Cambios aplicados

- `templates/base.html`
  - Se anadio `show_client_sidebar`.
  - Se anadio `show_client_topbar_nav` para dejar topbar publica sin duplicar cliente autenticado.
  - Se anadio `data-v885-shell`.
  - Se anadio comentario activo V885.
  - Se creo `aside.ns-client-sidebar` con enlaces reales.
  - Se mantuvo bottom nav para movil.
  - Se preservo admin rail.

- `static/app.css`
  - Se anadio bloque `V885 CLIENT SIDEBAR RESTORE BEST POSITION NAV`.
  - Desktop cliente muestra sidebar y desplaza contenido.
  - Movil oculta sidebar y muestra bottom nav.
  - Admin oculta sidebar cliente, bottom nav cliente y SHARK cliente.

- `engines/visual_company_worker_engine.py`
  - Se anadieron reglas `V885_NAV_RULES`.
  - Se detecta cliente autenticado sin sidebar, duplicados de sidebar/bottom nav y SHARK duplicado.

- `engines/continuous_shark_sentinel_engine.py`
  - Se anadieron reglas `V885_CLIENT_SIDEBAR_RESTORE_RULES`.

## No aplicado

- No se recuperaron railes legacy `v798/v799` como markup principal.
- No se creo otro menu paralelo.
- No se tocaron datos, pagos, Telegram ni secretos.
