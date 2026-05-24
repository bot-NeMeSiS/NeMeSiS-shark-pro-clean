# NeMeSiS SHARK PRO V507 - Premium Core Consolidation

Base: V506 sobre V505 limpia.

Objetivo: consolidar la experiencia premium sin romper rutas ni duplicar sistemas.

Incluye:
- Home premium real con accesos rapidos a Match Hub, Live, Hoy, Picks, Combis y Favoritos.
- Match Hub Global: live, proximos, populares, favoritos y top leagues.
- Favoritos reales en SQLite: equipos, ligas y partidos con feed personalizado.
- IA SHARK 2.0: briefing, respuesta contextual, picks explicados y analisis de riesgo.
- Telegram Auto Engine: scheduler tick, triggers, logs y anti duplicados.
- Live Depth: minuto, marcador, estado, timeline base y momentum visual preparado.
- Performance: cache persistente para Match Hub y endpoint de estado.

Rutas nuevas principales:
- /match-hub
- /partidos
- /partidos-hoy
- /favoritos
- /api/match-hub
- /api/favorites
- /api/favorites/feed
- /api/matches/<match_id>/timeline
- /api/shark/ask
- /api/telegram/scheduler-tick
- /api/telegram/triggers
- /api/telegram/logs
- /api/cache/status

Rutas existentes preservadas:
- /
- /global
- /calendario
- /live
- /admin/import-center
- /api/health
- /api/calendar
- /api/live
- /api/crest-diagnostics
- /api/diagnostics

Legalidad:
No scraping ilegal. Solo APIs permitidas, datos propios, importaciones autorizadas, cache persistente y revision editorial.

Render:
Mantener `DB_PATH=/data/database.db`.
