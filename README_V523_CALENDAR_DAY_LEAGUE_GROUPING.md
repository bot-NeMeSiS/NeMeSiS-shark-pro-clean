# NeMeSiS SHARK PRO V523 — Calendar Day + League Grouping

Avance global sobre V522 centrado en que el calendario deje de ser una lista suelta y se parezca más a una app deportiva premium.

## Incluye
- Calendario agrupado primero por día.
- Dentro de cada día, partidos agrupados por liga/competición.
- Dentro de cada liga, orden por hora.
- Badges por categoría: España, Internacional, Andalucía, UEFA y Selecciones.
- Filtros de Match Hub conservados: Hoy, Mañana, Semana, Live, España, Internacional, Andalucía, UEFA y Selecciones.
- Estados vacíos premium para cliente.
- CTA admin al Data Center cuando no haya datos.
- Diagnóstico `/api/matches/diagnostics` ampliado con partidos por día, liga y próximos 7 días.
- CSS responsive para móvil.

## Legalidad
No scraping. Solo usa datos persistidos legalmente desde TheSportsDB, The Odds API o importaciones CSV/JSON autorizadas.

## Deploy
Preparado para Render con SQLite persistente en `DB_PATH=/data/database.db`.
