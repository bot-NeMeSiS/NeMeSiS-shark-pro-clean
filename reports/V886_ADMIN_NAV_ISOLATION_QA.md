# V886 Admin Nav Isolation QA

## Rutas admin objetivo

- `/admin/dashboard`
- `/admin/continuous-sentinel`
- `/admin/visual-worker`
- `/admin/payments`

## Validacion aplicada

Sin sesion admin, las rutas y APIs deben bloquear o redirigir sin renderizar elementos cliente.

Se valida:

- No `data-nav-zone="client-sidebar"` en respuesta admin.
- No `data-nav-zone="client-bottom"` en respuesta admin.
- No `class="shark-widget"` cliente en respuesta admin.
- APIs admin sin sesion devuelven 403.
- Cron/master tick sin secret devuelve 403.

## Resultado esperado

Admin conserva su aislamiento visual y operativo. No se mezclan navegacion cliente ni floating SHARK cliente.
