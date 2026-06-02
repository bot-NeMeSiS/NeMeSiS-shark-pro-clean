# V603 — Startup Black Screen & Full App Repair

## Objetivo
Reparar el bloqueo de arranque que podía dejar la aplicación en negro al abrirla y consolidar la app actual hasta V602.

## Fallos corregidos
- Bloqueo SQLite durante el primer arranque: `init_db()` llamaba a motores con conexiones SQLite separadas antes de confirmar el esquema principal.
- Versión interna pisada por una asignación antigua `V582_TELEGRAM_PICKS_HARD_FIX_AUDIT_READY`.
- Inicio automático del scheduler demasiado agresivo por defecto. Ahora no se lanza al importar salvo que `AUTO_SYNC_ON_STARTUP=true` esté configurado explícitamente.
- Pequeños textos visibles con acentos y emoji SHARK corregidos en portada.

## Validación realizada
- `compileall app.py engines database_manager.py` OK.
- Plantillas Jinja parsean sin errores.
- Rutas principales probadas con Flask test client usando SQLite temporal:
  - `/api/health` OK
  - `/` OK
  - `/global` OK
  - `/calendario` OK
  - `/live` OK
  - `/match-hub` OK
  - `/resultados` OK
  - `/cliente-login` OK
  - `/registro` OK
  - `/membresias` OK
  - `/telegram` OK
  - `/shark` OK
  - `/picks` OK
  - `/recommendations` OK
  - `/combis` OK
  - `/api/v600/shark-accuracy-check` OK
  - `/api/v601/api-exploitation-check` OK
  - `/api/v602/player-intelligence-check` OK

## Nota Render
Para máxima estabilidad inicial, deja `AUTO_SYNC_ON_STARTUP` sin definir o en `false`. Si quieres que el scheduler arranque solo al iniciar Render, ponlo explícitamente en `true` cuando ya verifiques que la web abre bien.
