# V926 Admin Command Center Desktop QA

Rutas cubiertas:

- `/admin/dashboard`
- `/admin/automation-workforce`
- `/admin/autonomous-company-sentinel`
- `/admin/sentinel-issues`
- `/admin/sentinel-codex-outbox`
- `/admin/telegram/command-center`

Cambios:

- Cabeceras compactas sin espacio negro superior.
- KPIs en cuatro columnas y acciones en tres columnas.
- Tablas con scroll interno seguro y filas mas compactas.
- Dashboard oculta en desktop el hero duplicado y el strip historico V904.
- Browser QA sigue presentado como pendiente cuando no hay capturas.
- Navegacion cliente, bottom nav y preview cliente no aparecen en templates admin.
- Sin sesion, todas las rutas quedan protegidas y ninguna devuelve 500.

