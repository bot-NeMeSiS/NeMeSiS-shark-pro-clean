# V496 — Andalucía Deep Calendar Foundation

Avance añadido sobre V495 sin romper rutas anteriores.

## Incluye
- Ruta `/calendario-andalucia` y alias `/andalucia` / `/regional-andalucia`.
- API `/api/v496/andalucia-structure`.
- API `/api/v496/calendar-candidates`.
- API `/api/v496/regional-diagnostics`.
- Tabla SQLite persistente `regional_sources_v496`.
- Tabla SQLite persistente `regional_calendar_intake_v496`.
- Matriz Andalucía: provincias x categorías.
- Fuentes legales preparadas: RFAF, RFEF, carga manual admin y datasets abiertos.

## No hace scraping ilegal
Esta versión solo deja la estructura legal preparada para conectar fuentes autorizadas, carga manual admin o datasets abiertos.

## Siguiente paso recomendado
V497: importador CSV/Admin para jornadas regionales + clasificaciones básicas persistentes.
