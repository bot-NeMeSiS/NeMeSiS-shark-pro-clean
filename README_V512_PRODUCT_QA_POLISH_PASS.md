# NeMeSiS SHARK PRO V512 - Product QA & Polish Pass

Base local auditada: V509/V511 line.

Objetivo: pasada de QA y pulido de producto sin rehacer arquitectura ni meter funcionalidades grandes.

Incluye:
- Revision de rutas principales y alias visibles.
- Correccion de pantallas faltantes `/telegram` y `/escudos`.
- Navegacion superior mas coherente y navegacion inferior movil.
- Lazy loading en escudos de cards principales.
- Pulido de CTA de combis para evitar flujo feo cuando no hay picks.
- Versionado V512 y health alias `/v512-health`.
- Mantiene arquitectura Flask + engines.
- Mantiene `DB_PATH=/data/database.db`.

Rutas QA objetivo:
- `/`
- `/match-hub`
- `/live`
- `/picks`
- `/combis`
- `/perfil`
- `/favorites`
- `/shark`
- `/telegram`
- `/escudos`
- `/api/health`

Legalidad:
No scraping ilegal. Solo APIs permitidas, datos propios, importaciones autorizadas, cache persistente y revision editorial.
