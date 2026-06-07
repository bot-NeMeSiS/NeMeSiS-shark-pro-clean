# NeMeSiS SHARK PRO — PC2 Current Clean Render Ready

Build limpia generada desde el ZIP `BOT_APUESTAS buena.zip` del PC 2.

Verificado:
- `app.py` compila correctamente.
- `database_manager.py` y `engines/` compilan correctamente.
- Paquete limpio sin `.git`, `__pycache__`, bases de datos locales, logs ni ZIPs antiguos.
- Preparado para GitHub + Render.

Notas:
- `VERSION.txt` de la base indica `V520_TELEGRAM_AUTOMATIC_PREMIUM_DELIVERY_ENGINE`.
- La carpeta contiene documentación posterior V521/V522, pero el código verificado pertenece a la base subida desde el PC 2.

Variables clave Render:
- `DB_PATH=/data/database.db`
- `SECRET_KEY=...`
- `THESPORTSDB_API_KEY=...`
- `THESPORTSDB_KEY=...`
- `ENABLE_LIVE_API=true`
- `THE_ODDS_API_KEY=...`
- `ENABLE_ODDS_API=true`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`
