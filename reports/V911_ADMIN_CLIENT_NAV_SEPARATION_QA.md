# V911 Admin / Client Nav Separation QA

Version: `V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL`

## Fixes

- `templates/base.html` ahora calcula `is_client_area` excluyendo explicitamente superficies admin.
- `show_mobile_bottom_nav` queda limitado a publico no-admin o cliente autenticado no-admin.
- El rail admin reemplaza `Vista cliente` por `Vista publica` y `Salir` por `Cerrar sesion admin`.
- CSS V911 oculta en `.ns-admin` cualquier sidebar/bottom nav/floating SHARK de cliente si una capa antigua intenta renderizarlo.

## Checked surfaces

- `/admin-login`
- `/admin/dashboard`
- `/admin/shark-sentinel`
- `/admin/autonomous-company-sentinel`
- `/admin/sentinel-issues`
- `/admin/sentinel-codex-outbox`
- `/admin/not-found-events`

## Result

El check V911 valida que estas superficies no contengan `Salir cliente`, `data-nav-zone="client-bottom"`, `data-nav-zone="client-sidebar"` ni `shark-widget` cliente.
