# V759 FULL PROJECT INITIAL AUDIT

Versión detectada al inicio: `V755_TELEGRAM_PICK_CANDIDATE_NORMALIZATION_SCHEDULE_CERTIFICATION_FIX`.

## Estado real encontrado

- El código activo contenía la normalización Telegram V755 en `app.py`.
- Los motores V756, V757 y V758 ya existían en `engines/`:
  - `engines/client_app_premium_engine.py`
  - `engines/client_growth_engine.py`
  - `engines/adaptive_experience_engine.py`
- Las rutas V757 y V758 estaban registradas: `/app`, `/mi-app`, `/inicio`, `/panel-cliente`, `/experiencia`, `/modo-app`, `/adaptive`, `/adaptativo`.
- Las plantillas principales ya incluían bloques V756, V757 y V758.
- La versión activa no reflejaba esa fusión: `VERSION.txt` y `APP_VERSION` seguían en V755.

## Qué se conserva

- Telegram automático V755.
- Render Cron protegido por `AUTOMATION_SECRET`.
- `DB_PATH=/data/database.db`.
- Madrid Time.
- Usuarios, sesiones, membresías, picks, SHARK, favoritos y rutas existentes.
- Checks V748-V758 y herramientas de release.

## Qué se fusiona

- V755 queda como base para Telegram/Cron.
- V756 queda como capa premium cliente en Home, Picks, Calendar y Match Detail.
- V757 queda como centro app/trust/navegación.
- V758 queda como experiencia adaptativa PC/móvil.
- V759 añade una capa ligera de coherencia visual y comercial en Home, Picks, Calendar, Live y Track Record.

## Qué se limpia o excluye del ZIP

Detectado en carpeta local:

- `.git`
- `.venv`
- `.pytest_cache`
- `__pycache__`
- `release_output`
- `v636work`
- ZIPs antiguos dentro de `release_output`

No se borran carpetas dudosas de la máquina local; se excluyen del ZIP Render Ready.

## Qué no se toca para no romper

- `tools/render_cron_telegram_tick.py`
- `/api/automation/telegram/tick`
- `AUTOMATION_SECRET`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_TOKEN`
- `DB_PATH`
- Scheduler, cola Telegram, dedupe, envíos manuales y automáticos.

## Riesgos observados

- `app.py` sigue siendo grande y concentra mucha responsabilidad.
- Existen informes históricos en raíz que no afectan runtime, pero ensucian la carpeta local.
- La calidad de datos real depende de Render, disco persistente y APIs externas configuradas.
