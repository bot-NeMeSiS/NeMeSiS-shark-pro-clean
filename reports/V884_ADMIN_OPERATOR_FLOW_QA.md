# V884 Admin Operator Flow QA

## Pantallas admin revisadas

- /admin/dashboard
- /admin/company-os
- /admin/company-audit
- /admin/continuous-sentinel
- /admin/sentinel-workflow
- /admin/fix-pipeline
- /admin/data-center
- /admin/data-marketplace
- /admin/telegram/command-center
- /admin/shark-ai
- /admin/users
- /admin/memberships
- /admin/payments
- /admin/visual-worker

## Flujo esperado

Admin debe responder:

- que version local esta activa;
- que version hay en Render;
- que detecto Sentinel;
- que detecto Visual Worker;
- que rutas necesitan atencion;
- que tareas puede ejecutar con aprobacion;
- que no se debe automatizar.

## Estado V884

- APIs admin del Visual Worker siguen protegidas sin sesion.
- Cron Visual Worker sigue protegido por `AUTOMATION_SECRET`.
- No se mezclan nav cliente ni floating SHARK cliente dentro del admin como flujo valido.
- El worker avisa si hay demasiados enlaces cliente dentro de admin.

## Pendiente

- Prueba autenticada con credenciales admin reales no ejecutada.
- Render sigue en V855, por lo que admin real de produccion no certifica V884.
