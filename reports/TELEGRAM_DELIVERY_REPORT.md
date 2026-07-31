# Telegram Delivery Report

## Decision

PARTIAL.

## Generated

2026-07-31T12:29:20+02:00 Europe/Madrid.

| elemento | estado | evidencia | limitaci?n |
| --- | --- | --- | --- |
| Dry-run | PASS_LOCAL | dry_run_ok=True, would_send=False, sent=False | Sin candidatos porque no hay configuraci?n/datos en DB temporal. |
| Preview | PARTIAL | preview_available=False | Sin pick/candidato real en DB temporal. |
| Destino | PARTIAL | destinations_count=0 | TELEGRAM_CHAT_ID ausente en entorno actual. |
| Entrega real | PARTIAL | Mensajes enviados = 0. | No autorizada todav?a en este Gate. |
| Dedupe noticia | PASS | Clave estable: True | Simulaci?n t?cnica, no noticia real. |
| Dedupe partido | PASS | Clave estable: True | Simulaci?n t?cnica, no partido real. |
| Dedupe pick | PASS | Clave estable: True | Simulaci?n t?cnica, no pick real. |
| Dedupe resumen | PASS | Clave estable: True | Simulaci?n t?cnica, no resumen real. |
| Dedupe cola | PASS | first_queued=True; second_skipped=True; reason=duplicate. | DB temporal aislada. |

## Error Controls

| elemento | estado | evidencia | limitaci?n |
| --- | --- | --- | --- |
| destino_inexistente | BOT_NOT_IN_GROUP_OR_CHANNEL | Telegram no encuentra el grupo/canal configurado. | Revisar TELEGRAM_CHAT_ID y que el bot esté dentro del grupo/canal. |
| bot_sin_permisos | BOT_NOT_IN_GROUP_OR_CHANNEL | El bot no puede escribir porque fue expulsado o no tiene permiso. | Añadir de nuevo el bot y permitirle escribir. |
| canal_sin_admin | BOT_NOT_ADMIN_IN_CHANNEL | El bot no tiene permisos suficientes en el canal. | Hacer admin al bot en el canal o usar un destino donde pueda escribir. |
| html_invalido | TELEGRAM_PARSE_MODE_ERROR | Telegram rechazó el formato Markdown/HTML del mensaje. | Reintentar en texto plano y revisar caracteres especiales. |
| mensaje_largo | MESSAGE_TOO_LONG | El mensaje supera el tamaño permitido por Telegram. | Recortar secciones secundarias del mensaje premium. |

## Guardrails

- Producci?n modificada: no.
- Mensajes reales enviados: 0.
- Secretos expuestos: 0.
- Push/deploy/commit: no.
- DB real escrita: no.
- Evidencia de dry-run: `tmp/telegram_gate3_evidence.json`.


## Minimum Action

Completar test real controlado con un ?nico mensaje t?cnico despu?s de validar token, bot, destino y permisos.
