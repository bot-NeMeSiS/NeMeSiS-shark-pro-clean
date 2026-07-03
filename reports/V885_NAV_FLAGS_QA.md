# V885 Navigation Flags QA

## Flags reforzados

- `is_admin_area`: usuario admin.
- `is_client_area`: usuario autenticado no admin.
- `show_client_sidebar`: cliente autenticado.
- `show_client_topbar_nav`: visitante/no autenticado.
- `show_mobile_bottom_nav`: no admin.
- `show_admin_nav`: admin.
- `show_floating_shark`: cliente y no ruta SHARK.

## Reglas verificadas

- Cliente desktop tiene fuente sidebar.
- Cliente movil conserva bottom nav.
- Publico conserva topbar simple de entrada/registro.
- Admin conserva rail admin.
- Admin no renderiza sidebar cliente.
- Admin no renderiza bottom nav cliente.
- `/shark`, `/shark-ai`, `/shark-core` no duplican floating SHARK.

## Nota

El control fino de desktop/movil se hace por CSS responsive. El HTML mantiene una fuente canonica de sidebar cliente, pero solo se muestra en desktop.
