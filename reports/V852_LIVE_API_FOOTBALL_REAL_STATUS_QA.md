# V852 Live / API-Football Estado Real

## Problema
La pantalla podía mostrar API-Football activo y, a la vez, live/cache 0 sin explicar si era normal.

## Corrección
- `/live` distingue proveedor activo sin directos de fallo técnico.
- Cliente ve `Sin directos reales ahora mismo`.
- Se añade diagnóstico premium: proveedor activo, caché live y guard anti-gasto.
- No se hacen llamadas API por render.

## Estados
- Sin directos reales ahora mismo.
- Esperando proveedor.
- Caché live.
- Guard anti-gasto activo.

## Check
`tools/check_v852_live_api_football_real_status.py`.
