# V815 Match Lifecycle Real Data QA

## Resultado

Se creo `tools/check_v815_match_lifecycle_real_data.py`.

## Casos simulados

- Partido futuro: `UPCOMING`.
- Partido empezado sin score: `LIVE_PENDING`.
- Partido live con minuto/marcador: `LIVE`.
- Partido finalizado con marcador: `FT`.
- Partido de madrugada ya pasado sin marcador: `RESULT_PENDING`.
- Partido pasado sin score API: `RESULT_PENDING`.

## Reglas preservadas

- No inventar resultado.
- No inventar minuto.
- No inventar eventos.
- Madrid Time siempre.
- Si el proveedor no trae dato, se muestra pendiente/no disponible.

## Pantallas afectadas

- Calendar.
- Partidos.
- Live.
- Match detail.
- Sports hub/app center por contexto compartido.
