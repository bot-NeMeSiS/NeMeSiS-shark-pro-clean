# V885 Sentinel Navigation Rules QA

## Visual Worker

Se anadieron reglas:

- `client_desktop_sidebar_required`
- `client_mobile_bottom_nav_required`
- `admin_must_not_render_client_sidebar`
- `admin_must_not_render_client_bottom_nav`
- `client_must_not_render_admin_nav`
- `single_client_sidebar_instance`
- `single_bottom_nav_instance`
- `single_floating_shark_instance`
- `active_route_marker_required`
- `primary_client_links_required`

## Continuous Sentinel

Se anadio `client_sidebar_restore_rules_v885` al resumen Sentinel.

Tambien se ajusto la lectura de datos deportivos locales: si una pantalla no tiene filas reales pero ya muestra un estado seguro, Sentinel lo mantiene como aviso operativo en `safe_data_reality_notes` y no como incidencia abierta. Esto evita bajar el score por no inventar datos en local.

## Objetivo

Sentinel no debe dar una lectura demasiado optimista si el cliente autenticado pierde navegacion principal o si admin vuelve a mezclar navegacion cliente.
