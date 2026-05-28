# NeMeSiS SHARK PRO — V543 Betting Recommendation + Live Telegram QA

## Objetivo
Cerrar el flujo real de apuestas:

Live / calendario / cuotas → recomendaciones SHARK → picks publicables → combinadas → Telegram → diagnóstico global.

## Añadido
- Motor `engines/betting_recommendation_engine.py`.
- Tabla `betting_recommendations` con migración segura bajo demanda.
- Ruta cliente `/recomendaciones`.
- Ruta admin `/admin/betting-center`.
- API `/api/betting/recommendations`.
- API `/api/betting/generate`.
- API `/api/betting/convert-to-pick`.
- API `/api/system/full-betting-check`.
- API `/api/telegram/enqueue-recommendations`.

## Filosofía
- No se inventan picks como reales.
- Si hay cuotas cacheadas de The Odds API, se usan para score y selección.
- Si no hay cuotas, el partido pasa a watchlist/pre-pick.
- Solo el admin convierte una recomendación en pick publicado.

## Comprobación rápida
- `/api/health`
- `/api/system/full-betting-check`
- `/admin/betting-center`
- `/recomendaciones`
- `/picks`
- `/api/betting/recommendations?refresh=1`

## Render
Mantener:
- `DB_PATH=/data/database.db`
- `THE_ODDS_API_KEY`
- `ENABLE_ODDS_API=true`
- `THESPORTSDB_API_KEY`
- `THESPORTSDB_KEY`
- `ENABLE_LIVE_API=true`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
