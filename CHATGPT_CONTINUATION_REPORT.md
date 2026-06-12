# ChatGPT Continuation Report — V714 Telegram SHARK Client Polish Final

## Estado Inicial

La base actual era `V713_COMBIS15_SHARK_AI_FINAL`. Ya estaban funcionando Telegram automático por Render Cron, canal Telegram, cola, picks, SHARK AI, Sports Hub, Live, Calendar, Match Detail, Favoritos, Combis hasta 15, Admin, Cliente, Render, SQLite persistente y PWA.

El objetivo de V714 no era añadir módulos, sino pulir presentación, idioma, horarios, Telegram, SHARK y experiencia cliente.

## Cambios Realizados

- Versión actualizada a `V714_TELEGRAM_SHARK_CLIENT_POLISH_FINAL`.
- `VERSION.txt` actualizado.
- Motor central de localización deportiva reforzado.
- Añadida traducción centralizada de mercados deportivos.
- Añadido formato de fecha/hora en español y Europe/Madrid: Hoy, Mañana y día de semana.
- Telegram usa mejor hora visible, nombres localizados y mercados en castellano.
- SHARK muestra horarios más claros y mercados traducidos.
- Picks automáticos Telegram más estrictos:
  - bloquea partidos antiguos.
  - bloquea picks sin cuota real.
  - bloquea selecciones pendientes/no cerradas.
- Diagnóstico admin de Telegram incluye salud de auto picks:
  - candidatos.
  - enviables.
  - descartados.
  - faltan cuotas.
  - faltan escudos.
  - faltan horarios.
  - motivos de descarte.
- Pantalla cliente Telegram limpiada para no mostrar token/canal/configuración técnica.

## Estado Telegram

Telegram manual y canal estaban certificados previamente.

En V714 no se cambió el flujo Cron estable:

- `/api/automation/telegram/tick`
- `/api/automation/daily/run`
- `AUTOMATION_SECRET`
- dedupe
- cola

Se pulió el formato y se endureció qué puede salir como pick premium.

## Estado SHARK

SHARK mantiene respuestas sobre picks, combinadas, favoritos, directo y resumen del día. V714 mejora la presentación con hora contextual y mercado traducido. Sigue sin inventar cuotas ni partidos.

## Validación

- `python -m compileall .`: OK.
- `pytest -q`: no ejecutable porque pytest no está instalado en el entorno local.
- `tools/smoke_check.py`: OK con avisos históricos de endpoints V601/V602 no relacionados.
- Smoke Flask local:
  - `/`: 200.
  - `/version`: 200 y V714.
  - `/api/runtime-version`: 200.
  - `/login`: 200.
  - `/cliente-login`: 200.
  - `/admin-login`: 200.
  - `/registro`: 200.
  - `/sports-hub`: 200.
  - `/live`: 200.
  - `/calendar`: 200.
  - `/picks`: 200.
  - `/combis`: 200.
  - `/telegram`: 302 por login, correcto.
  - `/shark`: 200.
  - Cron sin secret: 403.
  - Cron con secret: 200.

## Pendiente Real

- Certificar recepción Telegram real en producción después de configurar Cron en Render.
- Verificar volumen de picks y cuotas con datos reales de API en producción.
- Instalar `pytest` si se quiere ejecutar la suite completa localmente.

## Conclusión

V714 deja la app más pulida para cliente, Telegram y SHARK sin romper el flujo estable de Render Cron ni las combinadas hasta 15.

