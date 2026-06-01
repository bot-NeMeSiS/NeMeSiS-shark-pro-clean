# NeMeSiS SHARK PRO — V532 Premium UX + Client Conversion Pass

Build completa Render-ready preparada sobre la base estable de rutas.

## Incluye
- Portada comercial diferenciada del panel cliente.
- Sección de membresías FREE / PRO / ELITE más clara.
- Página `/membresias` mejorada.
- Navegación pública con acceso a membresías.
- Accesos rápidos de cliente: calendario, resultados, live, picks, combis, favoritos, Telegram y SHARK IA.
- Nuevo diagnóstico `/api/client-experience-check`.
- Fix preventivo en detalle de partido para estadísticas Jinja.
- Mantiene login, perfil, admin, picks, combis, favoritos, calendario, resultados, live, equipos, SHARK y Telegram.

## QA
- `app.py` compila OK.
- Engines compilan OK.
- ZIP limpio sin `.git`, `__pycache__`, logs, DB local ni ZIPs antiguos.

## Deploy
Mantener en Render:
- `DB_PATH=/data/database.db`
- `SECRET_KEY`
- `THESPORTSDB_API_KEY`
- `THESPORTSDB_KEY`
- `THE_ODDS_API_KEY`
- `ENABLE_LIVE_API=true`
- `ENABLE_ODDS_API=true`
