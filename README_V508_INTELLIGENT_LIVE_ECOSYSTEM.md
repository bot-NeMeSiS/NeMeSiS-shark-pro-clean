# NeMeSiS SHARK PRO V508 - Intelligent Live Ecosystem

Base: V507 Premium Core Consolidation.

Objetivo: conectar sistemas entre si y dar sensacion de app viva sin rehacer la arquitectura.

Incluye:
- Live Data Flow: live, Match Hub, favoritos, picks y perfil comparten estado.
- Live State Engine: estados normalizados LIVE, HT, FT, UPCOMING y SUSPENDED.
- Match Detail Structure: timeline, eventos, estadisticas fallback, momentum y alineaciones futuras.
- Favorites Feed: partidos, live y picks relacionados con favoritos.
- Telegram Auto Core: scheduler manager, queue, anti duplicados, logs persistentes y alertas.
- SHARK AI Context: contexto persistente para partido, liga, favoritos y picks recientes.
- Performance: cache persistente y endpoints pensados para navegacion rapida.
- Clean Architecture: motores internos separados en `engines/live_engine.py`, `telegram_engine.py`, `shark_engine.py`, `crest_engine.py` y `cache_engine.py`.

Nuevas rutas/API:
- /api/live-flow
- /api/ecosystem/state
- /api/matches/<match_id>/detail
- /api/shark/context
- /api/telegram/queue
- /api/telegram/scheduler-manager
- /v508-health

Rutas anteriores preservadas:
- /
- /global
- /calendario
- /live
- /match-hub
- /favoritos
- /picks
- /combis
- /perfil
- /membresias
- /shark-ai
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
