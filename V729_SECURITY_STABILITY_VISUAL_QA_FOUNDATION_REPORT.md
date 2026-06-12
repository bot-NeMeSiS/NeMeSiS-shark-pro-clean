# V729 Security Stability Visual QA Foundation

Versión final: `V729_SECURITY_STABILITY_VISUAL_QA_FOUNDATION`

## Resumen ejecutivo

V729 es una versión quirúrgica sobre V728. No añade features grandes ni rehace la app. Refuerza seguridad real, estabilidad de sesión, formularios, rate limiting, cabeceras y pequeños textos visuales, manteniendo intactos Telegram V727, Madrid Time V728, Live/Calendar V726, Data Memory, picks, combis y SHARK.

## Cambios principales

### 1. SECRET_KEY profesional

- `app.secret_key` usa ahora `secure_secret_key()`.
- Se evita el fallback aleatorio que podía invalidar sesiones tras cada restart/deploy.
- En producción, la app debe exigir un `SECRET_KEY` real configurado en Render.

### 2. CSRF aplicado

- CSRF activo en métodos sensibles no exentos.
- Token expuesto en `base.html` mediante meta tag.
- Formularios POST renderizados reciben hidden input automáticamente.
- Fetch del widget SHARK y favoritos manda `X-CSRF-Token`.
- Cron y webhook quedan exentos para no romper automatizaciones externas.

### 3. Rate limiting

Se protege contra abuso:

- `/cliente-login`, `/login`, `/entrar`
- `/admin-login`
- `/registro`
- recuperación/cambio de contraseña
- `/api/admin/telegram/test-send`

### 4. Eventos de seguridad

- Login cliente/admin correcto y fallido registrado.
- Registro correcto/fallido registrado.
- Recuperación de contraseña registrada.
- Bloqueos de CSRF y rate limit registrados.

### 5. Cabeceras de seguridad

Se añaden cabeceras HTTP defensivas básicas sin romper la app.

### 6. Pulido visual/texto

- Correcciones de microcopy en castellano en pantallas seleccionadas.
- Se evita “Contrasena”, “sesion”, “membresias”, “proximos” sin acento en plantillas tocadas.
- No se rediseñó de nuevo V728 para evitar riesgo innecesario.

### 7. Limpieza HTML raíz

- Auditoría confirma 0 HTML duplicados en raíz del proyecto limpio V729.

## Validación ejecutada en sandbox

- `python -m py_compile app.py tools/check_v729_security.py tools/build_clean_release.py tools/audit_release_zip.py`: OK
- `python -m compileall -q app.py engines templates tools tests`: OK
- `python tools/check_v729_security.py`: OK
- `python tools/check_madrid_times.py`: OK
- `python tools/check_v728_client_experience.py`: OK
- `python tools/build_clean_release.py`: OK
- `python tools/audit_release_zip.py`: OK

## Limitaciones del entorno

El sandbox no tiene Flask instalado, por lo que:

- `tools/check_telegram_reliability.py` informa `DEPENDENCY_MISSING` por falta de Flask.
- `tools/smoke_check.py`, `tools/validate_release.py` y `pytest -q` deben ejecutarse en local/Render con dependencias instaladas.

Esto no se marca como éxito falso.

## Qué no se tocó

- No se tocaron secrets reales.
- No se cambió `AUTOMATION_SECRET`.
- No se cambió `DB_PATH=/data/database.db`.
- No se tocó Render real.
- No se envió Telegram real.
- No se rompió Telegram Command Center V727.
- No se rompió Madrid Time V728.
- No se rompió Live/Calendar/Sports Hub.
- No se migró `app.py` a blueprints todavía.

## Veredicto

V729 sube la base de seguridad y estabilidad sin hacer una cirugía peligrosa. El siguiente gran paso técnico recomendado ya no es seguir metiendo pantallas, sino extraer blueprints poco a poco en versiones separadas.
