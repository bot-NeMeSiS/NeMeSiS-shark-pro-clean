# V890 Runtime DBPATH + Telegram Premium QA Hardening

Version: `V890_RUNTIME_DBPATH_TELEGRAM_PREMIUM_QA_HARDENING_FINAL`.

Objetivo: seguir avanzando tras V889 corrigiendo un fallo real visto en smoke local: si `DB_PATH` no estaba definido, Windows intentaba usar `/data/database.db` y daba `Acceso denegado`.

Correccion aplicada:
- `DB_PATH` explicito por entorno sigue teniendo prioridad.
- Render sigue usando `/data/database.db` cuando existen variables Render.
- Local sin `DB_PATH` usa `data/database.db` dentro del proyecto.

Se preserva:
- V887 `QUEUE_SKIPPED`.
- V888 AutoPilot.
- V889 Telegram premium picks.
- No filler/dedupe.
- No envio real de Telegram.
- No secretos.
