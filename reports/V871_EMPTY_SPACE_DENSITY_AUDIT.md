# V871 Auditoría de Espacios Vacíos y Densidad

## Pantallas revisadas
Cliente: `/`, `/app`, `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/shark`, `/telegram`, `/profile`, `/track-record`, `/support`.

Admin: `/admin/dashboard`, `/admin/company-os`, `/admin/company-audit`, `/admin/continuous-sentinel`, `/admin/sentinel-workflow`, `/admin/fix-pipeline`, `/admin/data-center`, `/admin/telegram/command-center`, `/admin/shark-ai`, `/admin/users`, `/admin/memberships`, `/admin/payments`.

## Riesgos detectados
- Headers y heroes con demasiado padding en algunas vistas.
- Cards genéricas con aire excesivo.
- Empty states demasiado grandes cuando faltan datos.
- Tablas admin con demasiada altura por fila.
- Grids con separación alta en móvil.

## Decisión
Aplicar una capa CSS compacta V871, sin rediseño masivo ni datos inventados.
