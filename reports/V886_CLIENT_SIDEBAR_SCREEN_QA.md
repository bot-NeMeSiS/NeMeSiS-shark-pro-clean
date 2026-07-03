# V886 Client Sidebar Screen QA

## Rutas cliente desktop objetivo

- `/app`
- `/partidos`
- `/calendar`
- `/live`
- `/picks`
- `/shark`
- `/telegram`
- `/profile`
- `/track-record`
- `/support`

## Validacion aplicada

El check V886 renderiza rutas con sesion cliente PRO local y valida:

- `client-sidebar` aparece una sola vez.
- `client-bottom` aparece una sola vez.
- No aparece `v808-admin-rail` en cliente.
- No hay enlaces admin dentro de la navegacion cliente.
- No hay labels duplicados en sidebar.
- Hay marcador de ruta activa.
- Floating SHARK no se duplica fuera de `/shark`.

## Decision

V885 queda validada como restauracion correcta del menu lateral cliente a nivel HTML/CSS. Queda pendiente QA visual real con navegador para confirmar espaciado y overflow pixel a pixel.
