# V927 Sports PC Value QA

## Calendario

Filtros Hoy/Mañana/Semana/Resultados, fuente, ultima sync, cache y acceso a directo quedan juntos arriba. Resultados y escudos solo proceden del contexto real o fallback seguro.

## Live

Filtros En vivo/Proximos/Finalizados y estado del proveedor aparecen antes del board. Marcador y minuto no se completan si el proveedor no los entrega.

## Picks y cuotas

La tabla desktop exige mercado, seleccion y cuota para incluir un pick. Los incompletos siguen bloqueados; no se genera pick ni precio de relleno.

Los cuatro helpers safe context conservan `no_render_api_call=true`.
