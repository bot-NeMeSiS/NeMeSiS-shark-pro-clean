# NeMeSiS SHARK PRO V500 — Smart Crest Identity Engine

Avance global centrado en identidad visual de equipos y escudos, manteniendo legalidad.

## Incluye
- Ruta `/team-identity` y alias `/escudos`.
- API `/api/v500/resolve-crest?team=Cadiz`.
- API `/api/v500/team-identity`.
- Diagnóstico `/api/v500/identity-diagnostics`.
- Tabla SQLite persistente `team_identity_v500`.
- Normalizador de nombres y aliases.
- Fallback premium por iniciales si no hay logo legal.
- Política clara: no scraping ilegal, solo fuentes legales/licenciadas, mappings propios o APIs permitidas.

## Render
Mantiene compatibilidad con V499 y versiones anteriores.

Variables principales recomendadas:
- `DB_PATH=/data/database.db`
- `ENABLE_LIVE_API=true`
- `THESPORTSDB_KEY=123`
- `THE_ODDS_API_KEY=...`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`
