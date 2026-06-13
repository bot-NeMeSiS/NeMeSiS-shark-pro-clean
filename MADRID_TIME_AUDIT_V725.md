# Auditoría de hora Madrid V725

- Fuente: `fixtures`
- DB: `/data/database.db`
- Selftest: OK
- Partidos revisados: 2
- Alertas: {}

## Casos obligatorios
- `2026-06-12T19:00:00Z` -> `21:00` Madrid | esperado `21:00` | OK
- `2026-12-12T20:00:00Z` -> `21:00` Madrid | esperado `21:00` | OK

## Muestras
- `summer_case` Equipo Local vs Equipo Visitante | original `2026-06-12T19:00:00Z` | Madrid `Viernes 12/06 · 21:00` | OK
- `winter_case` Equipo Local vs Equipo Visitante | original `2026-12-12T20:00:00Z` | Madrid `Sábado 12/12 · 21:00` | OK
