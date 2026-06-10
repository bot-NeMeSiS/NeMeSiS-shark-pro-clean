# V712 — Spanish Time + Client Polish

Entrega incremental sobre V711 sin rehacer la app.

## Objetivo
Pulir la experiencia cliente después de revisar el vídeo:

- Equipos y selecciones en castellano cuando vengan de APIs en inglés.
- Competiciones y países visibles en castellano.
- Horarios normalizados a Europe/Madrid / hora española.
- Telegram mantiene el envío que ya funcionaba, pero ahora aplica nombres en castellano y hora española.
- Limpieza de textos cliente para que no aparezcan mensajes internos/admin donde no corresponde.
- Pulido de navegación visible: Directo, Inicio deportivo y wording más claro.

## Cambios principales

- Nuevo helper `engines/spanish_localization_engine.py`.
- `APP_VERSION = V712_SPANISH_TIME_CLIENT_POLISH`.
- Conversión de timestamps API UTC/Z/+00:00 a hora española.
- Normalización ligera en arranque de partidos cacheados con `kickoff_iso`.
- `sportsdb_event_to_match()` y `odds_event_to_match()` ya guardan fecha/hora local Madrid.
- `get_matches()`, `get_upcoming_matches()`, calendario agrupado y picks aplican campos seguros:
  - `safe_home`
  - `safe_away`
  - `safe_competition`
  - `safe_country`
  - `safe_time`
  - `safe_date`
- Telegram formatea nombres y horarios con castellano/hora española.
- Se revisan textos cliente para evitar menciones innecesarias a admin, QA o rutas internas.

## Ejemplos de normalización

- Mexico → México
- South Africa → Sudáfrica
- South Korea → Corea del Sur
- Czech Republic → República Checa
- Bosnia and Herzegovina → Bosnia y Herzegovina
- Cape Verde → Cabo Verde
- FIFA World Cup → Mundial FIFA
- World Cup → Mundial

## Validación

- `python -m compileall -q app.py engines` OK
- `pytest -q` OK: 12 passed
- `python tools/smoke_check.py` OK, con 2 warnings legacy ya conocidos de endpoints antiguos no bloqueantes.

## Render

Subir ZIP, desplegar y comprobar `/version`:

```text
V712_SPANISH_TIME_CLIENT_POLISH
```

Los Cron Jobs existentes de V710/V711 no cambian.
