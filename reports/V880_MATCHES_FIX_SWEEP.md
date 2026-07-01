# V880 Matches Fix Sweep

## Diagnóstico

No se inventan partidos. Si no hay partidos visibles, la app debe mostrar `Sin datos reales`, `Esperando proveedor`, `Sin sincronización reciente` o `Proveedor sin datos ahora mismo`.

## Riesgos revisados

- API configurada pero producción antigua.
- Cache/DB puede no estar poblada.
- Filtros pueden ocultar datos si no hay sincronización reciente.
- Render real no sirve V880 todavía.

## Corrección V880

Sentinel añade reglas para `matches_empty_without_safe_explanation` y `configured_api_without_visible_data_state`. No se hicieron llamadas caras ni sync masivo.
