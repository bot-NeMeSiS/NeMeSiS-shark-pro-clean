# V705 REAL COVERAGE AUDIT

## Estado local real

No se encontro base de datos deportiva local en la carpeta oficial. La app usa `DB_PATH=/data/database.db`, que pertenece al entorno Render/persistent disk. En el PC no se puede medir la cobertura real de produccion.

## Medicion controlada V705

- Ligas visibles: 10.
- Partidos visibles hoy: 18.
- Partidos visibles manana: 10.
- Partidos visibles semana: 28.
- Partidos live: 3.
- Picks visibles: 12.
- Candidatos a pick: 22.
- Recomendaciones generadas: 22.
- Partidos con cuotas reconocidas: 28.
- Partidos con SHARK/recomendacion: 22.
- Deportes visibles: 1 (futbol).
- Deportes/ligas de odds configuradas: 14.

## APIs/fuentes

- TheSportsDB: configurada en codigo, requiere `THESPORTSDB_KEY` o `THESPORTSDB_API_KEY`.
- The Odds API: configurada, requiere `THE_ODDS_API_KEY` y `ENABLE_ODDS_API=true`.
- Import legal CSV/JSON: disponible.
- SQLite warehouse/cache: disponible.
- Telegram: disponible, pero no es fuente deportiva.

## Datos que no llegan sin configurar

- Partidos reales actualizados.
- Live real.
- Cuotas reales.
- Resultados historicos por competicion.
- Escudos completos.
- Eventos/timeline avanzados.

## Que falta para medir produccion

Ejecutar en Render:

- `/api/matches/diagnostics`
- `/api/odds/diagnostics`
- `/api/data-center/summary`
- Sync de SportsDB.
- Sync de Odds.
- Revisar Sports Hub, Calendar, Live y Picks con DB persistente.
