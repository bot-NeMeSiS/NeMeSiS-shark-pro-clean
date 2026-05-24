# NeMeSiS SHARK PRO V504 - Clean Winner Core

Esta version limpia sustituye la acumulacion historica de versiones por un nucleo compacto, mantenible y listo para seguir creciendo.

## Que se conserva
- Futbol global premium.
- Competiciones principales mundiales y europeas.
- Calendario global.
- Andalucia como modulo diferencial, no como limite del producto.
- Centro de importacion legal CSV/JSON.
- Live Center basado en datos reales/importados.
- Escudos/fallback por iniciales sin depender de scraping.
- SQLite persistente.
- Render ready.

## Que se elimina
- Cientos de rutas historicas V80-V503 que ya no eran necesarias para avanzar.
- Plantillas antiguas duplicadas.
- Archivos de release acumulados.
- Modulos legacy que metian ruido al producto.

## Rutas principales
- `/`
- `/global`
- `/competiciones`
- `/calendario`
- `/calendario-global`
- `/live`
- `/live-center`
- `/admin/import-center`
- `/api/calendar`
- `/api/live`
- `/api/import-matches`
- `/api/diagnostics`
- `/v504-health`

## Politica de datos
No scraping ilegal. Solo APIs permitidas, datos propios, CSV/JSON autorizado, cache persistente y revision editorial.

## Siguiente avance recomendado
V505: conectar TheSportsDB/The Odds API con este core limpio y guardar snapshots reales en `matches`.
