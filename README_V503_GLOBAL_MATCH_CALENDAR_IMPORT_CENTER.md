# NeMeSiS SHARK PRO V503 - Global Match Calendar + Legal Import Center

V503 convierte la inteligencia global V502 en una app mas viva: calendario global, partidos priorizados y centro de importacion legal.

## Incluye
- Pantalla `/calendario-global`, con alias `/global-calendar` y `/partidos-global`.
- Admin `/admin/import-center`, con alias `/admin/legal-import`.
- API `/api/v503/calendar`.
- API `/api/v503/import-matches` para POST JSON o payload CSV.
- API `/api/v503/imports`.
- Diagnostico `/api/v503/diagnostics`.
- Health `/v503-health`.
- Tabla SQLite `global_matches_v503`.
- Tabla SQLite `legal_imports_v503`.
- Semillas visuales para calendario global mientras se cargan datos reales.
- Integracion con V502 para competiciones/carriles/prioridad.
- Integracion con V500 para escudos/fallback de equipos.

## Legalidad
No scraping ilegal. El centro acepta datos propios, APIs permitidas, CSV/JSON autorizado y cargas editoriales con nota legal.

## Render
Mantiene compatibilidad con V495, V499, V500, V501 y V502.

Variables recomendadas:
- `DB_PATH=/data/database.db`
- `ENABLE_LIVE_API=true`
- `THESPORTSDB_KEY=123`
- `THE_ODDS_API_KEY=...`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

## Siguiente camino natural
- V504 Global Live Center Pro conectado al calendario V503
- V505 SHARK AI Global Football Brain
- V506 Premium Telegram Global Segments
- V507 Favoritos globales y regionales
