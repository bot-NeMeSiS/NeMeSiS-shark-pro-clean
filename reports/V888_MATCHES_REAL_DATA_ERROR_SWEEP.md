# V888 Matches Real Data Error Sweep

## Revisión

Áreas revisadas:

- `/partidos`
- `/calendar`
- `/app`
- `/api/match-hub`
- filtros de calendario
- labels de fecha/competición

## Corrección V888

Se corrigieron labels visibles con mojibake en calendario:

- `Mañana`
- `Próximos`
- `España`
- `Andalucía`

## Estado de datos

No se inventaron partidos. Si no hay datos reales, la app debe seguir mostrando estados seguros:

- Sin partidos reales ahora mismo.
- Requiere sincronización real.
- Proveedor sin datos ahora mismo.
- Revisar filtros/fecha/cache.

