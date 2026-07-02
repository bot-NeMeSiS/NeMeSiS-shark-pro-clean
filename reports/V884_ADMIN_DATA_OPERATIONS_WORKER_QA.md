# V884 Admin Data Operations Worker QA

## Admin revisado
- Data center.
- API panels.
- Partidos/cache.
- Live/cache.
- Picks/odds.
- Logos.
- Telegram.
- Sentinel.
- Visual Worker.

## Estado
Las rutas admin revisadas por el worker local estan protegidas sin sesion y no devuelven 500.

## Necesidad operativa
Admin debe ser el lugar donde se explique por que no hay filas deportivas visibles:
- proveedor configurado o no;
- cache vacio;
- sync pendiente;
- filtros ocultando todo;
- temporada sin datos;
- logos cache 0 con fallback.

## Seguridad
No se muestran secretos. Las acciones reales de sync/proveedor requieren aprobacion.
