# NeMeSiS SHARK PRO V509 - Real Time Premium Sports Engine

Base: V508 Intelligent Live Ecosystem.

Objetivo: dar sensacion de plataforma deportiva viva en tiempo real sin rehacer la arquitectura.

Incluye:
- Real Time Match Engine con estado global, sincronizacion, refresco inteligente y fallback automatico.
- Estados compartidos: upcoming, live, halftime, finished y suspended.
- Live Visual Depth con minuto, marcador, badges, intensidad, timeline, eventos, momentum y estadisticas fallback.
- Global Match Hub 2.0 como nucleo principal: live, hoy, proximos, favoritos, top leagues y picks relacionados.
- Favorites Intelligence: prioriza favoritos, live relacionados y picks relacionados.
- Telegram Auto Engine V2 con scheduler manager, queue manager, anti duplicados, retries, logs y auto posts.
- SHARK AI Sports Context con partido actual, favoritos, picks recientes, ligas favoritas y estado live.
- Cache & Performance Engine con cache persistente, refresco inteligente y endpoints para navegacion rapida.
- Premium Mobile Feel con mejoras tactiles, spacing y tarjetas mas fluidas.
- Clean Architecture: `live_engine`, `match_engine`, `cache_engine`, `telegram_engine`, `shark_engine`, `crest_engine`.

Nuevas rutas/API:
- /api/realtime/state
- /api/live/state
- /api/telegram/auto-posts
- /v509-health

Rutas preservadas:
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
- /api/match-hub
- /api/live-flow
- /api/crest-diagnostics
- /api/diagnostics

Legalidad:
No scraping ilegal. Solo APIs permitidas, datos propios, importaciones autorizadas, cache persistente y revision editorial.

Render:
Mantener `DB_PATH=/data/database.db`.
