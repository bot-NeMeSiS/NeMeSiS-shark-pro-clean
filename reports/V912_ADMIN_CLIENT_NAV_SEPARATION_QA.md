# V912 Admin / Client Nav Separation QA

## Objetivo

Evitar que cualquier vista admin muestre navegación cliente, bottom nav, sidebar cliente o SHARK flotante de cliente.

## Pantallas revisadas localmente

- `/admin-login`
- `/admin/dashboard`
- `/admin/shark-sentinel`
- `/admin/autonomous-company-sentinel`
- `/admin/sentinel-issues`
- `/admin/sentinel-codex-outbox`
- `/admin/not-found-events`

## Resultado

- `is_admin_surface` cubre `/admin-login`, `/admin/*` y `/api/admin/*`.
- `show_mobile_bottom_nav` excluye superficies admin.
- `show_client_sidebar` solo se activa para usuario cliente autenticado y fuera de admin.
- `show_floating_shark` solo se activa en área cliente.
- CSS V912 oculta defensivamente elementos cliente si el body tiene `ns-admin`.

## Estado

OK local. No se hizo deploy ni se declara producción V912.
