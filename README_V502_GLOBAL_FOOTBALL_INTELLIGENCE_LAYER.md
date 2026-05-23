# NeMeSiS SHARK PRO V502 - Global Football Intelligence Layer

V502 corrige el foco de producto: NeMeSiS SHARK PRO pasa a organizarse como ecosistema futbolistico global premium, no solo regional.

## Incluye
- Nueva home global `/`.
- Nueva pantalla `/global-football`, con alias `/futbol-global` y `/competiciones`.
- API `/api/v502/global-football-hub`.
- API `/api/v502/competitions`.
- API `/api/v502/priority-engine`.
- Diagnostico `/api/v502/global-diagnostics`.
- Health `/v502-health`.
- Tabla SQLite persistente `global_competitions_v502`.
- Competiciones semilla: Mundial, Eurocopa, Copa America, Champions, Europa League, Conference, Premier, LaLiga, Serie A, Bundesliga, Ligue 1, Portugal, Eredivisie, MLS, Brasil, Argentina, Copa del Rey y Andalucia regional.
- Motor de prioridad: directo real, competicion top, favoritos, picks/combis, derbis/finales, Espana y Andalucia seguida.
- Andalucia se conserva como modulo diferencial dentro del mapa global.

## Legalidad
No se hace scraping ilegal. El sistema queda preparado para APIs permitidas, cache persistente, datos propios, carga editorial autorizada y transparencia de fuente.

## Render
Mantiene compatibilidad con V495, V499, V500 y V501.

Variables principales recomendadas:
- `DB_PATH=/data/database.db`
- `ENABLE_LIVE_API=true`
- `THESPORTSDB_KEY=123`
- `THE_ODDS_API_KEY=...`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

## Siguiente camino natural
- V503 Global Match Calendar
- V504 Global Live Center Pro
- V505 SHARK AI Global Football Brain
- V506 Legal Data Import Center
- V507 Premium Telegram Global Segments
