# V883 Product/Data Rules Model

El worker revisa el nucleo deportivo sin inventar datos.

## Reglas de producto real
- `/partidos` vacio sin estado seguro.
- `/calendar` vacio sin estado seguro.
- `/live` o `/directo` vacios sin explicar proveedor/sync.
- `/picks` vacio sin explicar revision o ausencia de picks activos.
- API configurada pero sin estado visible.
- Cache de partidos/live/odds/logos en 0 sin tarea o fallback.
- Picks sin cuota y sin estado `Cuota pendiente`.
- Seleccion pendiente mal comunicada.
- Pick en revision no explicado.
- Proveedor sin datos sin CTA.
- Filtros que ocultan todo sin reset.
- Falta de relacion visible partido -> pick cuando exista dato real.
- Estado de sync no visible.

## Estados seguros admitidos
- Sin partidos reales ahora mismo.
- Esperando proveedor.
- Sin sincronizacion reciente.
- Requiere sincronizacion real.
- Proveedor sin datos ahora mismo.
- Sin directos reales.
- Sin picks activos.
- Cuota pendiente.
- Seleccion pendiente.
- Pick en revision.
- Sin pick real publicado.
- No configurado.
- Accion pendiente.
- Modo seguro activo.
- Analisis limitado sin proveedor IA.
- Escudo pendiente.
- Fallback visual activo.
