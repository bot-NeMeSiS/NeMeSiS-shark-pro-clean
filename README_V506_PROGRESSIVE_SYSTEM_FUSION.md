# NeMeSiS SHARK PRO V506 - Progressive System Fusion

Base: V505 Smart Crest Fix.

Objetivo: fusionar progresivamente sistemas anteriores sin romper la base limpia.

Incluye:
- Telegram automatico seguro, sin enviar nada si faltan variables de entorno.
- Picks premium importables por CSV/JSON autorizado.
- Combis construidas solo sobre picks existentes.
- Perfil cliente premium persistente en SQLite.
- IA SHARK con briefing interno basado en datos reales/importados disponibles.
- Membresias Free, PRO y ELITE preparadas para capa comercial.
- Live real multi-fuente por importacion legal/API permitida.
- Escudos persistentes por cache SQLite, TheSportsDB o fallback SVG propio.

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

Nuevas rutas:
- /picks
- /combis
- /perfil
- /membresias
- /shark-ai
- /api/picks
- /api/import-picks
- /api/combis
- /api/combis/build
- /api/profile
- /api/membership
- /api/shark/briefing
- /api/telegram/status
- /api/telegram/send
- /api/telegram/auto-run
- /api/v495/telegram-auto-run
- /v506-health

Legalidad:
No scraping ilegal. Solo APIs permitidas, datos propios, importaciones autorizadas, cache persistente y revision editorial.

Produccion:
Mantener DB_PATH=/data/database.db en Render para SQLite persistente.
