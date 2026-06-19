# V816 Match Lifecycle Live Data QA

## Check

`tools/check_v816_match_lifecycle_real_data.py`

## Casos cubiertos

- Futuro => `UPCOMING`.
- Live => `LIVE`.
- Finalizado => `FT`.
- Empezado sin score => `LIVE_PENDING`.
- Madrugada pasada => `RESULT_PENDING`.
- Pasado sin score API => `RESULT_PENDING`.

## Reglas

- No se inventa marcador.
- No se inventa minuto.
- No se inventa evento.
- Si el proveedor no trae datos, se muestra pendiente/no disponible.
- Madrid Time se mantiene.
