# NeMeSiS SHARK PRO V501 - Global Andalucia Premium Ecosystem

V501 convierte la base V500 en una capa global de producto mas clara: ecosistema futbolistico premium inteligente con foco principal en Espana, Andalucia y futbol regional.

## Incluye
- Nueva pantalla `/andalucia`, con alias `/ecosistema` y `/andalucia-premium`.
- API `/api/v501/andalucia-hub`.
- API `/api/v501/regional-clubs`.
- Diagnostico `/api/v501/global-diagnostics`.
- Health `/v501-health`.
- Tabla SQLite persistente `regional_club_hub_v501`.
- Mapa base de las 8 provincias andaluzas.
- Clubes semilla andaluces conectados al motor de identidad V500.
- Modulos premium preparados: calendario regional, escudos, legal intake, live bridge, Telegram premium y SHARK AI local.

## Legalidad
No se hace scraping ilegal. La capa esta preparada para datos propios, APIs permitidas, CSV autorizado, mappings editoriales y fuentes con licencia controlada.

## Render
Mantiene compatibilidad con V495, V499 y V500.

Variables principales recomendadas:
- `DB_PATH=/data/database.db`
- `ENABLE_LIVE_API=true`
- `THESPORTSDB_KEY=123`
- `THE_ODDS_API_KEY=...`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

## Siguiente camino natural
- V502 Regional Calendar Real Import
- V503 Premium Telegram Segments
- V504 SHARK AI Local Match Briefing
- V505 Combi Regional Intelligence
