# NeMeSiS SHARK PRO — V506 GLOBAL ECOSYSTEM RECOVERY

Base: V505 Smart Crest Fix Clean.

## Avance V506

Esta versión recupera visión de app completa sin romper el core limpio:

- Centro de mando `/ecosistema`
- Módulos globales conectados: Live, Telegram, Picks, Perfil, IA, Escudos, Calendario
- Rutas nuevas:
  - `/ecosistema`
  - `/picks`
  - `/perfil`
  - `/telegram`
  - `/ia-shark`
  - `/escudos`
- APIs nuevas:
  - `/api/v506/ecosystem`
  - `/api/v506/picks`
  - `/api/v506/telegram`
  - `/api/v506/profile`
- Nuevas tablas SQLite:
  - `picks`
  - `telegram_queue`
  - `user_profile`
  - `app_modules`
- Mantiene importación legal CSV/JSON.
- Mantiene Smart Crest resolver y fallback SVG.
- Mantiene Render ready.

## Política legal

No scraping ilegal. No copiar webs privadas. No inventar datos live/cuotas/eventos. Solo APIs permitidas, datasets abiertos, datos propios o cargas autorizadas.

## Render

Variables clave:

```env
SECRET_KEY=
DB_PATH=/data/database.db
ENABLE_ODDS_API=true
ENABLE_LIVE_API=true
THE_ODDS_API_KEY=
THESPORTSDB_KEY=123
THESPORTSDB_API_KEY=123
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
OPENAI_API_KEY=
```

## Verificación rápida

```bash
python -m py_compile app.py
python app.py
```

Endpoints:

- `/api/health`
- `/api/diagnostics`
- `/api/v506/ecosystem`
