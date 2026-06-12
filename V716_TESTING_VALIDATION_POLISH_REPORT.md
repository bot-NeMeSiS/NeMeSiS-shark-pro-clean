# V716 Testing Validation Polish

## Objetivo

Preparar NeMeSiS SHARK PRO para que `pytest -q` pueda ejecutarse en local, Codex o entornos de validación instalando dependencias desde `requirements.txt`, sin tocar la lógica estable de V716, Render, Telegram automático, Cron, seguridad V715, DB_PATH ni experiencia cliente.

## Cambios realizados

### Dependencias

- Se añadió `pytest==8.3.4` a `requirements.txt`.
- Se actualizó `requirements-dev.txt` para heredar de producción con:
  - `-r requirements.txt`

Esto permite que un entorno simple ejecute:

```bash
pip install -r requirements.txt
pytest -q
```

### Tests

Se añadió `tests/test_v716_release_validation.py` con pruebas reales para:

- versión runtime esperada,
- rutas públicas principales sin 500,
- rutas cliente autenticadas sin 500,
- Cron sin secret devuelve 403,
- Cron con `AUTOMATION_SECRET` de test devuelve 200,
- endpoints técnicos protegidos devuelven 403 sin admin/secret,
- home pública no muestra versión técnica interna.

Se actualizó `tests/conftest.py` para establecer:

- `AUTOMATION_SECRET=pytest-automation-secret`

sin desactivar la seguridad real.

### Script de validación

Se creó `tools/validate_release.py`.

Ejecuta:

- `python -m py_compile app.py`
- `python -m compileall -q .`
- `python tools/smoke_check.py`
- `python -m pytest -q` si `pytest` está disponible

Si `pytest` no está instalado, muestra mensaje claro:

```bash
pytest no está instalado. Ejecuta:
pip install -r requirements.txt
pytest -q
```

## Archivos modificados

- `app.py`
- `VERSION.txt`
- `requirements.txt`
- `requirements-dev.txt`
- `tests/conftest.py`
- `tests/test_v716_release_validation.py`
- `tools/validate_release.py`
- `V716_TESTING_VALIDATION_POLISH_REPORT.md`

## Versión

Nueva versión:

`V716_TESTING_VALIDATION_POLISH`

Actualizado en:

- `APP_VERSION`
- `VERSION.txt`
- `/version`
- `/api/runtime-version`

## Validación ejecutada

- `python -m py_compile app.py`: OK
- `python -m compileall -q .`: OK
- `python tools/smoke_check.py`: OK
- `python tools/validate_release.py`: ejecuta py_compile, compileall y smoke OK; se detiene en pytest porque no está instalado.
- `python -m pytest -q`: no ejecutable en este entorno porque `pytest` no está instalado.

## Intento de instalación de pytest

Se intentó:

```bash
python -m pip install -r requirements.txt
```

Resultado:

- Flask, gunicorn, Werkzeug, Jinja2, itsdangerous, click y MarkupSafe ya estaban instalados.
- La instalación de pytest falló porque el entorno bloquea conexión a PyPI:
  - `Failed to establish a new connection`
  - `Intento de acceso a un socket no permitido por sus permisos de acceso`

Conclusión:

El proyecto queda preparado correctamente. En un entorno con red o caché de paquetes, `pip install -r requirements.txt` instalará pytest y permitirá ejecutar `pytest -q`.

## Smoke manual

Con Flask test client y DB temporal:

- `/`: 200
- `/version`: 200
- `/api/runtime-version`: 200
- `/login`: 200
- `/cliente-login`: 200
- `/admin-login`: 200
- `/registro`: 200
- `/sports-hub`: 200
- `/live`: 200
- `/calendar`: 200
- `/picks`: 200
- `/combis`: 200
- `/shark`: 200
- Cliente `/dashboard`: 200
- Cliente `/telegram`: 200
- Cliente `/favorites`: 200
- Cliente `/picks`: 200
- Cliente `/combis`: 200
- Cliente `/shark`: 200
- Admin `/admin/telegram/diagnostics`: 200
- `/api/automation/telegram/tick` sin secret: 403
- `/api/automation/telegram/tick?secret=...`: 200
- `/api/automation/daily/run` sin secret: 403
- `/api/automation/daily/run?secret=...`: 200
- `/api/runtime-version`: `V716_TESTING_VALIDATION_POLISH`
- Home pública no muestra versión técnica interna.

## Endpoints técnicos protegidos

Sin admin ni secret:

- `/api/diagnostics`: 403
- `/api/cache/status`: 403
- `/api/telegram/auto-run`: 403
- `/api/scheduler/status`: 403
- `/api/matches/diagnostics`: 403
- `/api/v601/api-exploitation-check`: 403
- `/api/v602/player-intelligence-check`: 403

## Impacto en Render, Telegram y Cron

- No se modificó el flujo Telegram.
- No se modificaron endpoints Cron.
- No se modificó `DB_PATH=/data/database.db`.
- No se modificó `AUTOMATION_SECRET`.
- No se tocó la lógica de envío automático ni scheduler.
- La única dependencia nueva es `pytest`, añadida para validación.

## Cómo probar en Render o entorno limpio

```bash
pip install -r requirements.txt
python -m py_compile app.py
python -m compileall -q .
python tools/smoke_check.py
python tools/validate_release.py
pytest -q
```

## Pendiente real

Nada de código queda pendiente para esta fase. Solo falta ejecutar `pytest -q` en un entorno donde se pueda instalar pytest desde `requirements.txt`.
