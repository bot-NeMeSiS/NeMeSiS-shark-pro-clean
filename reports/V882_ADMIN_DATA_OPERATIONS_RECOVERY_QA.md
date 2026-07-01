# V882 Admin Data Operations Recovery QA

## Revisión

Admin mantiene:

- Data Center.
- API-SPORTS.
- Company OS.
- Company Audit.
- Sentinel.
- Workflow.
- Scheduler/cron protegido.

## Lo que debe ver el dueño

Si no hay partidos/live/picks, la causa probable debe buscarse en:

- último sync;
- cache vacía;
- filtros;
- proveedor configurado sin datos;
- Render/local mismatch;
- DB_PATH local distinto de Render.

V882 documenta esa ruta operativa y añade Sentinel para no ocultarla.
