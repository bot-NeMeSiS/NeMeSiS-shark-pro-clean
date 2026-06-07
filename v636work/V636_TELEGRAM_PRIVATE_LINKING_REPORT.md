# V636 — Telegram Private Linking + Mobile Telegram Polish

## Base
Build aplicado sobre la base recibida, posterior a V635 Telegram Automatic Delivery Repair.

## Objetivo
Arreglar dos puntos detectados en producción:

1. El canal Telegram funcionaba, pero el usuario no podía vincular su chat privado con su cuenta NeMeSiS.
2. La pantalla Telegram ocupaba demasiado espacio en móvil y seguía diciendo que la vinculación automática estaría disponible próximamente.

## Cambios realizados

### Vinculación privada real de Telegram
- Añadidas columnas seguras a `users`:
  - `telegram_username`
  - `telegram_link_code`
  - `telegram_link_expires`
  - `telegram_linked_at`
- Añadido generador de código temporal de vinculación.
- Añadido enlace directo al bot con `https://t.me/<bot>?start=<codigo>`.
- El usuario puede vincular enviando al bot:
  - `/link NSP-XXXXXX`
  - `/start NSP-XXXXXX`
- El webhook `/telegram/webhook` ahora procesa `/start`, `/link` y `/vincular`.
- Al vincular, guarda:
  - `telegram_chat_id`
  - `telegram_username`
  - `telegram_linked_at`
- También sincroniza el usuario con `telegram_subscribers`, para que los envíos automáticos por membresía tengan destinatario real.

### APIs nuevas
- `/api/telegram/link-code`
- `/api/telegram/unlink`

### Pantalla Telegram mejorada
- `templates/telegram.html` reescrita.
- Ya no dice que la vinculación llegará próximamente.
- Muestra estado real:
  - conectado
  - pendiente
  - código de vinculación
  - bot destino
  - membresía
- Pantalla más compacta para móvil y web.

### CSS responsive
- Añadidos estilos V636 para:
  - página Telegram más compacta
  - tarjetas más pequeñas
  - código destacado
  - estado privado/canal
  - botón SHARK menos invasivo en móvil

## Validación
- `python -m compileall app.py engines database_manager.py services`: OK.

## Notas de uso
Para que el usuario reciba mensajes privados:

1. Entrar en NeMeSiS.
2. Abrir `/telegram`.
3. Pulsar “Abrir Telegram” o copiar el código.
4. Enviar al bot `/link NSP-XXXXXX`.
5. La app guardará el chat privado y los envíos automáticos podrán usar ese destinatario según membresía.

## Variables recomendadas
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME=nemesi_shark_pro_bot`
- `TELEGRAM_CHAT_ID` opcional para canal global.

## ZIP
Build limpio Render Ready.
