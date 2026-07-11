# V931 Home Data Consistency QA

## Problema corregido

La home calculaba `Partidos hoy` con una consulta y construia las cards con otra lista mas amplia. Eso permitia mostrar contador `0` y, debajo, partidos futuros o incompletos con `Competicion pendiente` y `Hora pendiente`.

## Fuente unica V931

`get_public_home_sports_summary()` devuelve:

- `valid_matches_today`
- `valid_matches_today_count`
- `valid_live_events`
- `valid_active_picks`
- `incomplete_matches`
- `provider_status`
- `last_sync`
- `safe_message`
- `no_render_api_call=true`

La plantilla usa `valid_matches_today` tanto para las cards como para el KPI. El contador es exactamente `matches|length`.

## Regla de validez

Un partido solo entra en el resumen principal cuando tiene:

- local y visitante reales;
- competicion real;
- fecha ISO valida;
- hora `HH:MM` valida;
- fuente real no marcada como placeholder.

No se inventan competicion, hora, liga, resultado, cuota ni fuente. Un registro incompleto se excluye del bloque principal y queda en `incomplete_matches` para diagnostico seguro.

## Prueba controlada

Fixture temporal, no datos visibles de produccion:

- 1 partido valido de hoy.
- 1 partido valido futuro.
- 3 registros incompletos: sin competicion, sin hora y sin fuente.
- KPI de hoy: 1.
- Cards validas visibles de hoy: 1.
- Incompletos separados: 3.
- Llamadas externas durante render: 0.

Resultado: no existe camino valido donde la home muestre `0` y liste partidos validos de hoy al mismo tiempo.
