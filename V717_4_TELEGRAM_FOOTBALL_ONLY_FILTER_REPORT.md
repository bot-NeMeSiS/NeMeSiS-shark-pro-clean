# V717.4 — Telegram Football Only Filter

## Objetivo

Dejar Telegram automático centrado únicamente en fútbol. La app puede seguir conservando estructura futura multi-deporte, pero el canal automático PRO no debe enviar baloncesto, NBA, tenis u otros deportes.

## Cambios principales

- Versión actualizada a `V717_4_TELEGRAM_FOOTBALL_ONLY_FILTER`.
- Añadido motor central `engines/telegram_sport_filter_engine.py`.
- Telegram queda por defecto en modo `football_only`.
- Añadidas variables de configuración en `.env.example`, `env.example` y `.env.render.clean`:
  - `TELEGRAM_SPORT_MODE=football_only`
  - `TELEGRAM_FOOTBALL_ONLY=true`
- Filtro aplicado a:
  - resumen diario Telegram
  - picks diarios Telegram
  - auto picks Telegram
  - alertas live Telegram
  - motor autónomo Telegram
  - diagnóstico de auto picks
  - formateadores premium Telegram
- Los candidatos no fútbol se descartan con motivo `deporte_no_futbol`.
- Admin diagnostics recibe `sport_filter` y `sport_mode` para confirmar la calibración.
- Añadidas columnas futuras `sport_key` en `matches` y `picks` sin romper tablas existentes.
- Añadidos tests específicos en `tests/test_telegram_football_only_filter.py`.

## Qué bloquea

- Baloncesto
- NBA
- WNBA
- Euroleague Basketball
- NCAA
- Tenis
- Baseball
- Hockey
- Rugby
- UFC/MMA
- Otros deportes detectables por sport_key, liga, competición o raw_json

## Qué permite

- Football
- Soccer
- Fútbol
- Mundial FIFA
- UEFA
- LaLiga
- Premier League
- Serie A
- Bundesliga
- Ligue 1
- Copa América
- Libertadores
- Andalucía/fútbol regional

## Validación local

- `python -m py_compile app.py engines/telegram_delivery_engine.py engines/telegram_autonomous_delivery_engine.py engines/telegram_sport_filter_engine.py`: OK
- `python -m compileall -q .`: OK
- Prueba directa del filtro:
  - NBA / basketball_nba: bloqueado con `deporte_no_futbol`
  - Mundial FIFA / soccer_fifa_world_cup: permitido
- `tools/smoke_check.py`: no se pudo completar en este entorno porque no hay Flask instalado. El proyecto mantiene `requirements.txt` para validarlo en local/Render.

## Cómo probar en Render

1. Desplegar el ZIP.
2. Abrir `/api/runtime-version` y confirmar `V717_4_TELEGRAM_FOOTBALL_ONLY_FILTER`.
3. Entrar en `/admin/telegram/diagnostics` y revisar:
   - `sport_filter.mode = football_only`
   - descartes por `deporte_no_futbol` si entran candidatos de basket/u otros deportes.
4. Probar Cron Tick/Daily con el secret oculto.
5. Confirmar que Telegram solo manda picks/alertas/resúmenes de fútbol.

## Notas

No se ha tocado Render, Cron, DB_PATH, secrets, login ni membresías. Esta versión solo refuerza el filtrado deportivo de Telegram automático.
