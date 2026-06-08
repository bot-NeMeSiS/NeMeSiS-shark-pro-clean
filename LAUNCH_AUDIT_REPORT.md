# LAUNCH AUDIT REPORT - V700 Ultimate Launch Edition

## Resumen ejecutivo

NeMeSiS SHARK PRO queda unificada como `V700_ULTIMATE_LAUNCH_EDITION` y preparada como candidata de lanzamiento comercial. La intervenci?n se centr? en estabilidad Render, arranque seguro, Telegram autom?tico, recuperaci?n de contrase?a, observabilidad admin y smoke tests reales.

## Errores encontrados

- `APP_VERSION` estaba duplicado en `app.py` y segu?a mostrando `V640_TELEGRAM_AUTO_ENV_SYNC_FIX`.
- `VERSION.txt` no estaba unificado con la release final.
- `rows()` segu?a disparando `seed_core()`, lo que mantiene riesgo arquitect?nico de que una consulta SQL active migraciones/seed.
- `/api/health` consultaba base de datos y estado deportivo, por lo que no era ultraligero para Render.
- `/` cargaba `dashboard_data()`, demasiado pesado para la primera petici?n y HEAD de Render.
- Faltaban rutas de recuperaci?n de contrase?a cliente/admin.
- Exist?an templates de observabilidad, pero las rutas `/admin/observability`, `/admin/observability/errors` y APIs asociadas no estaban conectadas.
- `/admin/intelligence` devolv?a 404 pese a existir inteligencia admin en `/admin/unified-intelligence`.
- Login cliente/admin cargaban `dashboard_data()` para pintar formularios.

## Correcciones aplicadas

- Versi?n final unificada: `V700_ULTIMATE_LAUNCH_EDITION` en `app.py` y `VERSION.txt`.
- `SEED_LOCK` mantiene inicializaci?n segura y reentrante.
- `rows()` queda como SELECT puro, sin seed ni migraciones.
- A?adida `initialize_once()` idempotente para rutas normales.
- A?adido `before_request` defensivo que excluye health, runtime, startup-check, service-worker y home.
- `/api/health` ahora responde sin tocar DB.
- A?adido `/api/startup-check` para comprobar DB/seed/admin de forma controlada.
- `/` usa `home_light_data()` y no carga dashboard pesado.
- Login, admin-login y registro usan datos ligeros.
- A?adida tabla `password_reset_tokens` con ?ndice seguro.
- A?adidas rutas:
  - `/forgot-password`
  - `/reset-password/<token>`
  - `/admin-forgot-password`
  - `/admin-reset-password/<token>`
- Recuperaci?n de contrase?a con token seguro, expiraci?n 30 minutos, un solo uso y respuesta silenciosa si el email no existe.
- SMTP preparado con variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`.
- Si SMTP no est? configurado, la app entra en modo diagn?stico sin romper.
- Reconectadas rutas de observabilidad admin y APIs JSON.
- `/admin/intelligence` redirige al centro unificado existente.
- Corregido texto visible `Contrasena` a `Contrase?a` en login cliente/admin.

## Telegram

Verificado en c?digo y smoke test:

- `get_telegram_settings()` mantiene heal-on-read desde variables Render.
- `_telegram_sync_env_on_startup()` existe.
- `ENABLE_TELEGRAM_AUTO=true` y `AUTO_SEND_TELEGRAM_PICKS=true` activan el autom?tico si token y chat global existen.
- `/api/telegram/link-status` responde 200.
- `/telegram/webhook` acepta `/start CODIGO` y `/link CODIGO`.
- `/admin/telegram` y `/admin/telegram/diagnostics` responden 200.

La prueba con Telegram fue simulada/local para no llamar a la API real desde el entorno sin red.

## Pruebas realizadas

Compilaci?n:

```bash
python -m compileall app.py engines database_manager.py services
```

Resultado: OK.

Smoke tests con Flask test client y base temporal:

- `/`: 200
- `/login`: 200
- `/cliente-login`: 200
- `/admin-login`: 200
- `/registro`: 200
- `/forgot-password`: 200
- `/admin-forgot-password`: 200
- `/api/health`: 200
- `/api/runtime-version`: 200
- `/api/startup-check`: 200
- `/dashboard`: 200
- `/perfil`: 200
- `/picks`: 200
- `/live`: 200
- `/calendar`: 200
- `/sports-hub`: 200
- `/favorites`: 200
- `/combis`: 200
- `/telegram`: 200
- `/shark`: 200
- `/recomendaciones`: 200
- `/telegram/webhook` con `/start CODIGO`: 200
- `/telegram/webhook` con `/link CODIGO`: 200
- `/api/telegram/link-status`: 200
- `/admin/dashboard`: 200
- `/admin/users`: 200
- `/admin/telegram`: 200
- `/admin/telegram/diagnostics`: 200
- `/admin/backups`: 200
- `/admin/automation`: 200
- `/admin/intelligence`: 302 hacia `/admin/unified-intelligence`
- `/admin/observability`: 200
- `/admin/observability/errors`: 200
- `/api/observability/summary`: 200
- `/api/observability/errors`: 200
- `POST /forgot-password`: 200
- `POST /admin-forgot-password`: 200

Errores 500 detectados en smoke: 0.

## Variables Render necesarias

Obligatorias para producci?n:

- `SECRET_KEY`
- `DB_PATH=/data/database.db`
- `ADMIN_EMAIL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`

SMTP recuperaci?n contrase?a:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`

APIs deportivas, si se usan en producci?n:

- `THESPORTSDB_API_KEY`
- `THE_ODDS_API_KEY`
- `API_FOOTBALL_KEY`

## Pendiente real

- Probar Telegram real contra Bot API desde Render con variables reales y red activa.
- Configurar SMTP real en Render para activar emails fuera del modo diagn?stico.
- Seguir enriqueciendo picks con datos reales de cuotas/mercados cuando las APIs est?n pobladas.
- Ejecutar QA visual manual en m?vil real antes de venta p?blica.
