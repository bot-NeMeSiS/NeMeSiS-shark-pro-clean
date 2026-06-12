# NeMeSiS SHARK PRO — V522 Global App Restructure + Picks Command Center

Build limpia preparada desde la base del PC2, consolidada para Render/GitHub.

## Incluye

- Limpieza de estructura para entregar una build estable sin `.git`, logs, DB local ni cachés.
- `app.py` verificado por compilación.
- Versionado actualizado a `V522_GLOBAL_APP_RESTRUCTURE_PICKS_COMMAND_CENTER`.
- Centro admin de picks en `/admin/picks`.
- APIs de picks:
  - `/api/picks`
  - `/api/picks/create`
  - `/api/picks/update`
  - `/api/picks/publish`
  - `/api/picks/archive`
  - `/api/picks/stats`
- Modelo de picks ampliado con:
  - mercado
  - bookmaker
  - stake unidades
  - stake ejemplo euros
  - confianza
  - riesgo
  - razonamiento
  - advertencia
  - membresía requerida
  - estado de resultado
  - fecha de publicación
- Página cliente `/picks` filtrada por membresía FREE/PRO/ELITE.
- `/combis` preparado para usar solo picks publicados reales, sin inventar combinadas sin base suficiente.
- Integración Telegram daily picks usando solo picks publicados.
- Tabla `user_activity` para preparar memoria futura de usuario.
- Mejoras visuales premium para cards, badges, navegación y móvil.

## Política de datos

- No scraping ilegal.
- No partidos ni picks falsos presentados como reales.
- Si no hay datos, se muestran estados vacíos premium.
- Datos deportivos previstos desde TheSportsDB Premium, The Odds API e import legal CSV/JSON.

## Variables recomendadas en Render

```txt
SECRET_KEY=
DB_PATH=/data/database.db

THESPORTSDB_API_KEY=
THESPORTSDB_KEY=
ENABLE_LIVE_API=true

THE_ODDS_API_KEY=
ENABLE_ODDS_API=true
ODDS_REGIONS=eu
ODDS_MARKETS=h2h,totals
ODDS_CACHE_MINUTES=20
LIVE_CACHE_MINUTES=2

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
OPENAI_API_KEY=
```

## Rutas principales a probar

```txt
/api/health
/
/cliente-login
/registro
/perfil
/match-hub
/live
/picks
/combis
/admin-login
/admin/data-center
/admin/picks
/admin/telegram
/api/picks
/api/picks/stats
```
