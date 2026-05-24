# NeMeSiS SHARK PRO V519 — Live Experience 2.0 + Match Detail System

## Incluye
- Página de detalle individual de partido: `/partido/<match_id>` y `/match/<match_id>`.
- Timeline visual premium con fallback legal.
- Estadísticas visuales preparadas para datos oficiales futuros.
- Momentum visual ampliado.
- Acciones rápidas hacia favoritos, picks y SHARK IA.
- APIs nuevas:
  - `/api/matches/<match_id>/detail`
  - `/api/matches/<match_id>/timeline`
  - `/api/matches/<match_id>/statistics`
- Enlaces desde Live y Match Hub hacia el detalle vivo.
- V518 completa mantenida: login, usuarios, admin, Telegram automático, SportsDB, SQLite seguro.

## Nota legal
No se inventan eventos oficiales. Si una fuente legal no entrega timeline/estadísticas, la app muestra un fallback visual claro y preparado.

## Deploy
Render-ready con `DB_PATH=/data/database.db`.
