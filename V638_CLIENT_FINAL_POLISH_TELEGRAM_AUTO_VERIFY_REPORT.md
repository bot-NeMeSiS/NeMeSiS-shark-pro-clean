# V638 Client Final Polish + Telegram Auto Verify

## Telegram automático verificado

- `/telegram` como cliente abre 200.
- `/api/telegram/link-status` genera código de vinculación.
- `/telegram/webhook` acepta `/start CODIGO` y vincula usuario.
- `/telegram/webhook` acepta `/link CODIGO` y vincula usuario.
- `enqueue_daily_picks()` encola picks para usuarios vinculados y canal admin.
- `process_premium_telegram_queue()` procesa cola y marca mensajes como `sent`.
- El segundo encolado del mismo día evita duplicados mediante `dedupe_key`.
- Se verificaron prueba privada y prueba canal con envío HTTP simulado para no depender de red externa.

## Panel Telegram

- `/admin/telegram` compactado y orientado a diagnóstico operativo.
- `/admin/telegram/diagnostics` devuelve 200 con JSON de salud.
- Añadidos indicadores:
  - bot configurado
  - canal configurado
  - usuarios vinculados
  - cola pendiente
  - últimos mensajes enviados
  - últimos errores
  - último envío automático
  - último pick enviado
  - duplicados evitados
- Añadidas acciones admin:
  - Procesar cola ahora
  - Enviar prueba privada
  - Enviar prueba canal
  - Reparar automático
  - Reintentar fallidos

## Experiencia cliente

- `/telegram` cliente compactado: estado, código, abrir bot, plan y qué recibe.
- `/calendar` restaurado como alias y rediseñado en lista compacta deportiva.
- Calendario con filtros en español: Hoy, Mañana, Esta semana, Próximos.
- `/sports-hub` restaurado como pantalla cliente compacta.
- `/live`, `/calendar`, `/sports-hub` y detalle de partido muestran estrella de favorito.
- Navegación cliente incluye acceso claro a Combis.
- CSS V638 añadido para reducir altura de héroes, tarjetas grandes y espacio muerto.

## Rutas restauradas

- `/calendar`
- `/sports-hub`
- `/api/runtime-version`
- `/admin/automation`
- `/admin/backups`
- `/admin/backups/download/<name>`

## Validación

- `compileall` OK sobre `app.py`, `engines`, `database_manager.py` y `services`.
- Smoke test:
  - `/`: 200
  - `/login`: 302 por sesión activa
  - `/cliente-login`: 302 por sesión activa
  - `/admin-login`: 200
  - `/registro`: 302 por sesión activa
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
  - `/admin/dashboard`: 200
  - `/admin/telegram`: 200
  - `/admin/telegram/diagnostics`: 200
  - `/admin/automation`: 200
  - `/admin/backups`: 200
  - `/api/health`: 200
  - `/api/runtime-version`: 200
- Observability errors en prueba: 0.

## Notas

- La prueba de envío Telegram usa simulación local de `telegram_send_http` por no depender de red en QA local. Valida cola, deduplicación, destinatario, estados y marcado `sent`.
- En producción, con `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` reales, el mismo procesador usa la API real de Telegram.

