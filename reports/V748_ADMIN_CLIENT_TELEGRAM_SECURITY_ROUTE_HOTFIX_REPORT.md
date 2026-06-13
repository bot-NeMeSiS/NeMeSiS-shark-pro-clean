# V748 Admin Client Telegram Security Route Hotfix

## Estado

Versión final: `V748_ADMIN_CLIENT_TELEGRAM_SECURITY_ROUTE_HOTFIX`.

Esta intervención corrige fallos reales detectados en auditoría sin rehacer la app, sin tocar secrets, sin cambiar `DB_PATH`, sin enviar Telegram real y sin romper Madrid Time.

## Errores corregidos

### Admin Data Center y Matches Sync

- Causa real: plantillas con variable Jinja corrupta `matches_díagnostics`.
- Corrección: normalizada a `matches_diagnostics`.
- Validación:
  - `/admin/data-center`: 200
  - `/admin/matches-sync`: 200

### Ruta duplicada `/partidos`

- Causa: `/partidos` estaba registrada en calendario y Match Hub.
- Corrección: `/partidos` queda solo en calendario premium.
- Se mantienen:
  - `/calendar`
  - `/calendario`
  - `/calendario-global`
  - `/partidos`
  - `/partidos/calendario`
  - `/match-hub`
  - `/partidos-hoy`
  - `/resultados`

### SHARK Core

- Causa: `v570_shark_core_summary()` llamaba a `build_daily_briefing()` con argumentos que la firma local no aceptaba.
- Corrección: `build_daily_briefing()` acepta contexto opcional: favoritos, recomendaciones, picks, live, próximos y membresía.
- Validación:
  - `/shark-core`: 200 con sesión cliente.

### API Admin Control Center

- Añadido `/api/admin/control-center`.
- Protegido por admin.
- Devuelve:
  - versión
  - Telegram sin secrets
  - DB/Data Memory/Data Vault
  - membresías temporales
  - cron/automation
  - rutas críticas
  - últimos errores seguros

### Enlaces legacy

- Añadidos aliases seguros:
  - `/membresías` -> membresías
  - `/soporte` -> soporte/contacto
  - `/seguimiento` -> track record
  - `/admin/live-depth` -> live QA admin

### APIs técnicas abiertas

Ahora están protegidas:

- `/api/diagnostics`: admin-only
- `/api/cache/status`: admin-only
- `/api/matches/diagnostics`: admin-only
- `/api/odds/diagnostics`: admin-only
- `/api/telegram/auto-run`: admin o `AUTOMATION_SECRET`
- `/api/profile`: sesión cliente

Validación:

- APIs técnicas sin sesión devuelven 401/403.
- Cron/auto-run sin secret: 403.
- Cron/auto-run con secret: 200.

### Membresías temporales

- Reforzada migración segura con `membership_admin_granted`.
- Se mantienen columnas:
  - `membership_source`
  - `membership_started_at`
  - `membership_expires_at`
  - `membership_note`
  - `membership_updated_at`
  - `membership_updated_by`
  - `membership_admin_granted`
- No borra historial.
- Caducidad automática baja a FREE.

### Admin

- Navegación principal alineada:
  - Control
  - Clientes
  - Membresías
  - Picks
  - Telegram
  - Datos
  - QA/Venta
  - Vista cliente
  - Salir

## Validaciones ejecutadas

- `python -m compileall -q app.py engines tools`: OK
- Parse Jinja plantillas principales: OK
- Smoke Flask rutas cliente/admin/cron: OK
- Madrid Time: OK
- Seguridad: OK
- Home Data: OK
- Telegram Automation: OK
- Telegram Destinations: OK
- Telegram Message Format: OK
- Data Vault: OK
- Production Readiness: OK
- Top App Readiness: OK
- V748 Hotfix Check: OK

## Limitaciones locales

- No se envió Telegram real.
- No se validaron secrets reales de Render.
- No se probó canal/privado real de Telegram en producción.

## ZIP

El ZIP final debe generarse con `tools/build_clean_release.py` y auditarse con `tools/audit_release_zip.py`.

Política:

- Sin `.git`
- Sin `.venv`
- Sin cachés
- Sin logs
- Sin bases locales
- Sin backups reales
- Sin vídeos
- Sin ZIPs internos
- Sin secrets
