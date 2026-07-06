# V897 Sentinel Issues Reconciliation QA

## Problema

`data/runtime/sentinel_issues_memory.json` podía conservar incidencias antiguas como abiertas aunque el smoke actual ya no reprodujera el fallo.

## Estados añadidos

- `STALE_NEEDS_REVALIDATION`
- `RESOLVED_BY_RESCAN`

## Reglas

- Si una incidencia se reproduce, se mantiene activa y suben sus occurrences.
- Si no se reproduce en el scan actual, pasa a `STALE_NEEDS_REVALIDATION`.
- Si acumula tres scans sin reproducirse, pasa a `RESOLVED_BY_RESCAN`.
- No se borra historial.
- No se muestran issues stale/resueltos por rescan como críticos activos.

## Validación

El check V897 crea una incidencia crítica artificial, ejecuta reconciliación sin candidatos y valida la transición:

`OPEN -> STALE_NEEDS_REVALIDATION -> RESOLVED_BY_RESCAN`

