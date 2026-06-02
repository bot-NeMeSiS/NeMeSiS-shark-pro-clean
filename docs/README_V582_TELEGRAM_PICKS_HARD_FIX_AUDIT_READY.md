# V582 — Telegram Picks Hard Fix Audit Ready

Objetivo: cerrar el fallo donde las pruebas Telegram llegan pero los picks no.

Cambios:
- Migraciones reforzadas para `telegram_queue` en bases SQLite antiguas: `alert_type`, `target_key`, `created_at`.
- `telegram_config()` ahora considera válido Telegram si existe `TELEGRAM_BOT_TOKEN` y hay destino por `TELEGRAM_CHAT_ID` o suscriptor activo vinculado.
- Mantiene endpoints de auditoría y envío real:
  - `/api/telegram/audit-picks`
  - `/api/telegram/fix-picks`
  - `/api/telegram/send-picks-now?force_empty=1`
  - `/api/telegram/process-queue?force=1`
- Compilación Python comprobada con `python -m py_compile app.py`.

Después de desplegar:
1. Entrar en Admin > Telegram.
2. Ejecutar Auditoría Picks.
3. Ejecutar Reparar settings.
4. Ejecutar Enviar picks ahora.
5. Revisar logs recientes si falla.
