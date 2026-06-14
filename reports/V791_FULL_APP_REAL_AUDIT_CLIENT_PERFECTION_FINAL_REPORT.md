# V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL

## Objetivo

Revisión real del ZIP completo enviado por Damian y cierre de una capa de perfección cliente sin rehacer la app ni tocar sistemas críticos.

## Cambios principales

- Añadido `engines/client_screen_audit_engine.py` para auditar pantallas cliente, rutas críticas, CSS, textos sensibles, legibilidad y ruido técnico.
- Añadido panel admin `/admin/client-screen-audit` con API `/api/admin/client-screen-audit`.
- Añadido enlace admin a `Lanzamiento real` y `Cliente` en la navegación admin.
- Corregido bug latente: `BASE_DIR` queda definido globalmente para auditorías V774/V776/V777/V778/V790 que ya lo usaban.
- Refinado lenguaje cliente para evitar promesas o términos de riesgo comercial: `Combi segura` pasa a `Combi responsable`, `Qué apostar` pasa a `Selección recomendada` o `Qué recomienda SHARK`.
- Mejoras CSS V791 sobre la capa V790: más aire en cards de directo/calendario, equipos con dos líneas, hover limpio en PC, mejor lectura móvil, legal footer más compacto.
- Mantenida la capa legal V787/V788: +18, juego responsable, no somos casa de apuestas, sin garantías y aceptación legal antes del checkout.

## Guardrails preservados

- No se tocó `DB_PATH`.
- No se tocaron usuarios, sesiones ni membresías existentes.
- No se tocó Telegram, Cron ni `/api/automation/telegram/tick`.
- No se tocó Stripe core, webhook, portal ni checkout.
- No se tocó Madrid Time.
- No se inventan partidos, picks, cuotas, resultados, ROI ni highlights.
- El ZIP final debe seguir limpio: sin `.git`, `.venv`, bases locales, logs, vídeos ni ZIPs internos.

## Pantallas cliente objetivo

- `/`
- `/app`
- `/calendar`
- `/live`
- `/picks`
- `/combis`
- `/mercados`
- `/match/<id>`
- `/highlights`
- `/track-record`
- `/shark`
- `/telegram`
- `/mi-cuenta`
- `/membresias`
- `/menu`
- `/legal`
- `/terminos`
- `/privacidad`
- `/juego-responsable`
- `/no-somos-casa-de-apuestas`

## Validación esperada

- `python -m py_compile app.py engines/client_screen_audit_engine.py`
- `python -m compileall -q app.py engines tools`
- Jinja parse de todas las templates.
- `python tools/check_madrid_times.py`
- Checks V782-V791.
- `python tools/build_clean_release.py`
- `python tools/audit_release_zip.py`

## Nota honesta

El entorno de esta conversación no tiene Flask instalado, por lo que el smoke Flask real debe ejecutarse en Render o local con dependencias instaladas. La V784 mantiene herramientas de smoke/preflight para esa prueba.
