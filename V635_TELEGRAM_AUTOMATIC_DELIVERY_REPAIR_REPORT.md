# V635 — Telegram Automatic Delivery Repair

## Objetivo
Arreglar el caso real donde Telegram manual funciona desde admin, pero el envío automático no llega a los clientes.

## Causa probable corregida
El flujo manual forzaba el envío y podía saltarse ajustes/cola, pero el flujo automático dependía de varios puntos que podían quedar desconectados:

- `telegram_settings.enabled` podía quedar desactivado en bases antiguas.
- Usuarios con `users.telegram_chat_id` no siempre estaban sincronizados en `telegram_subscribers`.
- El procesador de cola podía saltarse si el automático estaba desactivado aunque existieran token y destinatarios.
- Faltaba una acción directa de reparación/diagnóstico automático desde admin.

## Cambios aplicados

### app.py
- Versión actualizada a `V635_TELEGRAM_AUTOMATIC_DELIVERY_REPAIR`.
- Añadido `telegram_auto_enabled_by_default()`.
- `get_telegram_settings()` ahora crea ajustes por defecto con automático activado si no se desactiva expresamente.
- Si existe token + destino válido, puede reactivar Telegram automático de forma segura.
- Añadido `sync_telegram_subscribers_from_users()` para copiar usuarios con `telegram_chat_id` a `telegram_subscribers`.
- `telegram_subscribers()` sincroniza usuarios antes de devolver destinatarios.
- `process_premium_telegram_queue()` ya no bloquea el automático si la configuración permite auto-envío.
- `telegram_scheduler_delivery()` repara ajustes seguros cuando procede.
- Añadido `repair_telegram_automatic_delivery()`:
  - activa ajustes seguros,
  - sincroniza suscriptores,
  - encola partidos,
  - encola picks,
  - procesa cola,
  - genera auditoría antes/después.
- Añadida API admin `/api/telegram/repair-automatic`.
- Añadida pantalla/alias `/admin/telegram/diagnostics`.

### templates/admin_telegram.html
- Añadido acceso a “Diagnóstico automático”.
- Añadido botón “Reparar automático”.
- Corregida referencia visual a `auto_live_alerts`.

## Variables recomendadas en Render

Para mantener el automático activo:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_AUTO_ENABLED=true
AUTO_SEND_TELEGRAM_PICKS=true
ENABLE_TELEGRAM_AUTO=true
```

Para desactivarlo explícitamente:

```env
DISABLE_TELEGRAM_AUTO=true
```

## Validación realizada

- `python -m py_compile app.py`: OK.
- `python -m compileall -q app.py engines database_manager.py services`: OK.
- Comprobación estática de funciones nuevas: OK.

No se ha ejecutado envío real a Telegram desde este entorno porque requiere credenciales de Render y acceso externo al bot.

## Flujo esperado tras desplegar

1. Entrar como admin.
2. Ir a `/admin/telegram/diagnostics`.
3. Pulsar “Reparar automático”.
4. Revisar:
   - suscriptores activos,
   - cola pendiente,
   - mensajes enviados hoy,
   - errores recientes.
5. Ejecutar la automatización diaria o esperar al ciclo programado.

## Resultado esperado
El envío automático debe seguir el flujo completo:

SHARK / Auto Picks / Daily Automation → picks válidos → cola Telegram → destinatarios por membresía → procesamiento → envío → log/observabilidad.
