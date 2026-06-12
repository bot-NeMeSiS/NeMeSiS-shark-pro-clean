# V715 Launch Audit Security Polish Final

## Objetivo

Auditoría real de lanzamiento para endurecer seguridad, separar cliente/admin, proteger endpoints técnicos y entregar un ZIP limpio Render Ready sin romper Render, SQLite, Telegram automático, Cron Jobs, SHARK AI ni combinadas hasta 15.

## Fallos Reales Encontrados

- No existía `.gitignore`, por lo que era fácil volver a incluir `.venv`, bases locales, cachés, logs, backups o ZIPs antiguos.
- Varias APIs técnicas quedaban accesibles sin sesión admin ni `AUTOMATION_SECRET`:
  - diagnósticos.
  - cache status.
  - imports.
  - observabilidad.
  - scheduler.
  - Telegram legacy/manual.
  - data center.
  - syncs SportsDB/Odds.
  - checks internos V7xx/V5xx.
- No había protección CSRF central para formularios HTML POST.
- No había cabeceras de seguridad básicas centralizadas.
- La pantalla cliente de Telegram había sido limpiada en V714, pero el backend aún permitía demasiada exposición técnica por API.

## Cambios Aplicados

- Versión actualizada a `V715_LAUNCH_AUDIT_SECURITY_POLISH_FINAL`.
- Añadido `.gitignore` con exclusión de:
  - `.git`, `.venv`, `venv`, `env`.
  - `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`.
  - bases locales SQLite y sidecars WAL/SHM.
  - logs, backups, temporales, ZIPs y `v636work`.
- Añadida configuración segura de cookies:
  - `SESSION_COOKIE_HTTPONLY=True`.
  - `SESSION_COOKIE_SAMESITE=Lax`.
  - `SESSION_COOKIE_SECURE=True` en Render/producción.
- Añadidas cabeceras:
  - `X-Frame-Options=SAMEORIGIN`.
  - `X-Content-Type-Options=nosniff`.
  - `Referrer-Policy=strict-origin-when-cross-origin`.
  - `Permissions-Policy` restrictiva.
  - `Cache-Control=no-store` en zonas admin/Telegram/scheduler.
- Añadida protección CSRF central para formularios HTML POST.
- Añadido inyector automático de `_csrf_token` en formularios POST renderizados desde `base.html`.
- Añadido bloqueo central de APIs internas:
  - admin-only o `AUTOMATION_SECRET`.
  - Cron actual mantiene acceso por secreto.
  - APIs públicas de cliente/deporte siguen disponibles.
- Protegidos endpoints legacy de Telegram automático/manual si no hay admin o secreto.
- Protegidos diagnósticos y syncs internos.

## Archivos Principales Modificados

- `app.py`
- `templates/base.html`
- `.gitignore`
- `VERSION.txt`
- `V715_LAUNCH_AUDIT_SECURITY_POLISH_FINAL_REPORT.md`

## Validación Ejecutada

- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines database_manager.py services blueprints tools tests`: OK.
- `python -m compileall -q .`: OK.
- `python tools/smoke_check.py`: OK sin warnings.
- `pytest -q`: no ejecutado porque `pytest` no está instalado en el entorno local.

Smoke Flask local con base temporal:

- `/`: 200.
- `/version`: 200 y muestra `V715_LAUNCH_AUDIT_SECURITY_POLISH_FINAL`.
- `/api/runtime-version`: 200.
- `/login`: 200.
- `/cliente-login`: 200.
- `/admin-login`: 200.
- `/registro`: 200.
- `/sports-hub`: 200.
- `/live`: 200.
- `/calendar`: 200.
- `/picks`: 200.
- `/combis`: 200.
- `/shark`: 200.
- `/telegram`: 302 a login, correcto.
- `/admin/telegram/diagnostics`: 302 a admin-login sin sesión, correcto.
- `/api/automation/telegram/tick`: 403 sin secret.
- `/api/automation/telegram/tick?secret=...`: 200 con secret.
- `/api/automation/daily/run`: 403 sin secret.
- `/api/automation/daily/run?secret=...`: 200 con secret.
- `/api/diagnostics`: 403 sin admin/secret.
- `/api/cache/status`: 403 sin admin/secret.
- `/api/telegram/auto-run`: 403 sin admin/secret.
- `/api/scheduler/status`: 403 sin admin/secret.
- `/api/matches/diagnostics`: 403 sin admin/secret.
- `/api/v601/api-exploitation-check`: 403 sin admin/secret y 200 con secret.
- `/api/v602/player-intelligence-check`: 403 sin admin/secret y 200 con secret.

Validación de seguridad:

- Login renderiza `_csrf_token`.
- POST a login sin CSRF: 403.
- Cabeceras presentes: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`.

## Qué Revisar en Render

- `AUTOMATION_SECRET` configurado.
- Cron Jobs siguen usando:
  - `/api/automation/telegram/tick?secret=...`
  - `/api/automation/daily/run?secret=...`
- `DB_PATH=/data/database.db`.
- `SESSION_COOKIE_SECURE` activo en producción.
- Admin puede acceder a diagnósticos tras login.
- Usuario cliente no ve endpoints técnicos ni secretos.

## Advertencias Honestas

- La recepción real de Telegram depende de Render Cron y del canal/bot reales configurados.
- Volumen de picks, cuotas y partidos depende de datos reales de The Odds API/TheSportsDB y del estado de la base persistente.
- CSRF protege formularios HTML. APIs JSON siguen funcionando con sesión admin, login o `AUTOMATION_SECRET` según corresponda.
