# TELEGRAM DELIVERY REPORT

Fecha Madrid: 2026-07-30
Modo: read-only / no send
Produccion modificada: false
Telegram enviado: false

## Decision

TELEGRAM DELIVERY: PARTIAL

El producto contiene cola, deduplicacion, retry, limites y memoria de entrega. La evidencia de produccion disponible no permite confirmar ultima entrega, ultimo error ni permisos reales del destino.

## Controles de entrega

| Control | Estado | Evidencia | Limitacion |
|---|---|---|---|
| Cola | PARTIAL | Tabla `telegram_queue` existe en el modelo; endpoints de cola/status estan protegidos | No se pudo leer contenido de cola en produccion sin sesion admin. |
| Dedupe | PASS | Existe indice unico `idx_telegram_queue_dedupe`; `enqueue_telegram_message` omite duplicados sin `force` | No se valido dedupe con datos productivos por falta de acceso admin. |
| Ultima entrega | BLOCKED_BY_ACCESS | Campos disponibles en `telegram_reliability_snapshot` y admin status | `/api/admin/telegram/status` y `/api/telegram/status` devuelven 403. |
| Ultimo error | BLOCKED_BY_ACCESS | Campos disponibles en snapshot/admin status | Requiere admin read-only. |
| Retry | PASS | `telegram_send_http` reintenta en texto plano si Telegram rechaza HTML; cola usa `attempts < max_attempts` | No se provoco error real. |
| Throttle | PASS | Ventanas silenciosas, limites por hora y por dia en `process_premium_telegram_queue` | No se forzaron envios reales. |
| Rate limit | PASS | Diagnostico clasifica `RATE_LIMITED`; test local valida bloqueo por limite diario | No se ejercito rate limit real de Telegram. |
| Mensajes multiples | PASS | Gate 3 no envio mensajes; no ejecuto scheduler ni process queue | Sin evidencia de entrega real. |
| Entrega a canal | PARTIAL | Destino global configurado | Permisos no certificados. |
| Entrega privada | BLOCKED_BY_ACCESS | Requiere listado de subscribers admin | No visible sin sesion admin. |

## Pruebas locales seguras

Se ejecutaron 8 pruebas especificas como funciones directas porque el runtime incluido no tiene `pytest` instalado.

Resultado: PASS 8/8.

Cobertura validada:

- filtro football_only bloquea NBA;
- filtro football_only permite UEFA, LaLiga y FIFA;
- falta de chat_id se clasifica como `MISSING_CHAT_ID`;
- limite diario se clasifica como `BLOCKED_BY_DAILY_LIMIT`;
- ausencia de cuotas explica no envio;
- modo Telegram por defecto es football_only.

## Endpoints observados sin sesion

| Endpoint | HTTP | Interpretacion |
|---|---:|---|
| `/api/admin/telegram/status` | 403 | Protegido. |
| `/api/admin/telegram/dry-run` | 403 | Protegido. |
| `/api/admin/telegram/preview-next` | 403 | Protegido. |
| `/api/admin/telegram/dedupe-status` | 403 | Protegido. |
| `/api/admin/telegram/environment-audit` | 403 | Protegido. |
| `/api/telegram/status` | 403 | Protegido. |
| `/api/telegram/diagnostics` | 403 | Protegido. |
| `/admin/telegram/command-center` | 302 | Redirige a login. |

## Resultado

Delivery no puede ser PASS sin una de estas dos evidencias:

1. prueba controlada autorizada de un unico mensaje a un destino de test, con log de entrega y dedupe;
2. o lectura admin/Telegram API read-only que certifique token, chat, permisos, ultima entrega, ultimo error y cola sin enviar mensaje.
