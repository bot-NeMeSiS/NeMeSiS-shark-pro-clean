# V772 Telegram Visual Cards Runbook

## Objetivo

Enviar mensajes Telegram más premium, con tarjeta visual cuando sea posible y texto seguro cuando no.

## Variables Render recomendadas

```env
TELEGRAM_VISUAL_CARDS_ENABLED=true
TELEGRAM_SEND_PICK_CARDS=true
TELEGRAM_SEND_COMBI_CARDS=true
TELEGRAM_SEND_RESULT_CARDS=true
TELEGRAM_SEND_HIGHLIGHT_CARDS=true
TELEGRAM_SEND_LIVE_CARDS=false
```

## Dependencia

Render instalará `Pillow==10.4.0` desde `requirements.txt`.

Si Pillow falla o no está disponible, la app no rompe Telegram: usa texto premium.

## Flujo

1. Render Cron llama `/api/automation/telegram/tick`.
2. V771/V772 planifica actividad real.
3. Si hay pick/combi/resultado/highlight válido, se encola.
4. La cola procesa el mensaje.
5. Si la tarjeta se puede generar, Telegram usa `sendPhoto`.
6. Si no, Telegram usa `sendMessage`.
7. Dedupe evita duplicados por mensaje y destino.

## Verificación admin

Revisar:

- `/admin/telegram/diagnostics`
- `/api/admin/telegram/activity-plan`
- `/api/admin/telegram/message-preview`
- `/api/admin/telegram/dedupe-status`

## Decisiones de seguridad

- No se descargan escudos externos para generar tarjetas.
- No se inventan datos.
- Live cards quedan desactivadas por defecto para evitar ruido.
- El canal global y privados mantienen la lógica existente.
