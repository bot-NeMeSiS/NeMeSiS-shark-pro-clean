# V719_PICKS_QUALITY_LEAGUES_CASTELLANO

## Objetivo
Mejorar la calidad comercial de los picks y asegurar que ligas/campeonatos/mercados se muestren en castellano de forma consistente.

## Cambios principales
- Nueva versión: `V719_PICKS_QUALITY_LEAGUES_CASTELLANO`.
- Nuevo motor `engines/picks_quality_engine.py`.
- Ranking de picks por calidad real: cuota, selección clara, mercado, competición, riesgo, timing, motivo y precaución.
- Nuevos campos en cada pick normalizado:
  - `quality_score`
  - `quality_label`
  - `quality_bucket`
  - `premium_ready`
  - `competition_priority`
- Los picks premium ahora priorizan señales listas con cuota real y selección clara.
- Los picks débiles o incompletos pasan a `En estudio por SHARK`.
- Telegram usa picks enriquecidos por calidad y evita publicar como premium picks que no estén listos.
- Ligas y campeonatos ampliados en castellano, incluyendo claves de API tipo `soccer_spain_la_liga`, `soccer_fifa_world_cup`, Champions, Europa League, Conference, LaLiga, Segunda, Premier, Serie A, Bundesliga, Ligue 1, Libertadores, Sudamericana, etc.
- Añadidos filtros Jinja:
  - `competition_es`
  - `market_es`
- Mejorada `/picks` con KPIs más comerciales y sección clara de `Picks premium listos` / `En estudio por SHARK`.
- Mejorada `/combis` con selector profesional segura/media/larga y selector compacto 2-15.
- `pytest==8.3.4` añadido a `requirements.txt` para mantener validación profesional.

## Archivos principales tocados
- `app.py`
- `VERSION.txt`
- `engines/spanish_localization_engine.py`
- `engines/picks_quality_engine.py`
- `engines/telegram_delivery_engine.py`
- `templates/picks.html`
- `templates/combis.html`
- varias plantillas con filtro `competition_es`
- `static/app.css`
- `requirements.txt`
- `requirements-dev.txt`

## Validación ejecutada
- `python -m py_compile app.py engines/picks_quality_engine.py engines/telegram_delivery_engine.py engines/spanish_localization_engine.py`: OK
- `python -m compileall -q app.py engines templates`: OK
- Parseo Jinja de 96 templates: OK
- Pruebas directas de motor de calidad/ligas/selección:
  - `soccer_spain_la_liga` -> `LaLiga EA Sports`
  - `UEFA Champions League` -> `Champions League`
  - `Away` en Inglaterra vs Croacia -> `Gana Croacia`
  - pick con cuota real -> `premium_ready=True`

## Validación no ejecutada completa
- `tools/smoke_check.py` no pudo completarse en este entorno porque no está instalado Flask: `No module named 'flask'`.
- El ZIP mantiene `requirements.txt`; en local/Render validar con:

```bash
pip install -r requirements.txt
python tools/smoke_check.py
pytest -q
```

## Qué comprobar en Render
- `/api/runtime-version` debe mostrar `V719_PICKS_QUALITY_LEAGUES_CASTELLANO`.
- `/picks` debe mostrar picks premium solo si tienen cuota/selección/mercado claros.
- Los picks incompletos deben ir a `En estudio por SHARK`.
- Ligas/campeonatos deben verse en castellano.
- Telegram debe seguir solo fútbol y con calibración PRO.
- Cron sin secret debe devolver 403.
- Cron con secret debe devolver 200.

## No tocado
- Render.
- DB_PATH.
- AUTOMATION_SECRET.
- Cron Jobs.
- Login/registro.
- Membresías.
- Telegram solo fútbol.
- Calibración PRO.
