# V885 Preflight - Client Sidebar Restore

Version objetivo: V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_FINAL

## Base local

- Carpeta oficial: C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro
- VERSION.txt previo: V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL
- APP_VERSION previo: V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL
- Base preservada: V881 nav root fix, V882 core product recovery, V883 Visual Company Worker y V884 functional flow.

## Archivos revisados

- templates/base.html
- static/app.css
- templates/partials/brand_logo.html
- templates/partials/ui_components.html
- engines/visual_company_worker_engine.py
- engines/continuous_shark_sentinel_engine.py

## Confirmacion

- No se uso ZIP viejo V827.
- No se trabajo en carpeta anidada.
- No se tocaron secretos.
- No se enviaron mensajes Telegram reales.
- No se tocaron pagos reales.
- No se inventaron partidos, picks, cuotas, resultados ni escudos.

## Resultado preflight

V881 habia retirado el rail cliente para evitar duplicados y dejo el cliente PC apoyado en topbar. V885 restaura una fuente lateral unica para cliente autenticado en desktop y mantiene bottom nav solo para movil.
