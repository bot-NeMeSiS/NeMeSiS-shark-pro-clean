# DATA MEMORY AUDIT V721

## Objetivo
Confirmar qué datos deportivos se guardan ya y reforzar la memoria histórica para futuro SHARK/analytics/ML sin romper Render, Cron ni Telegram.

## Estado auditado

| Dato | Estado antes | Refuerzo V721 | Uso futuro |
|---|---|---|---|
| Partidos | Tabla `matches` + histórico parcial | `match_snapshots` normalizados desde Daily Run | Evolución de calendario, cobertura, dedupe, ligas útiles |
| Equipos / escudos | `teams`, logos en `matches`, motor V718 | `team_identity_cache` interno | Mejor cobertura visual y calidad por equipo |
| Cuotas | `odds_snapshots` existente y odds en picks/matches | `odds_memory_snapshots` preparado para snapshots normalizados | Cambios de cuota, value real, timing |
| Live | `live_matches`, profundidad SHARK | `live_memory_snapshots` preparado | Señales live y momentum histórico |
| Picks | Tabla `picks` | `pick_decisions` registra guardados/candidatos Telegram | Rendimiento por mercado/liga/cuota |
| Picks descartados | Logs/diagnóstico Telegram | `pick_discards` con motivo estructurado | Saber por qué SHARK descarta señales |
| Telegram | `telegram_deliveries`, `telegram_queue` | `telegram_delivery_memory` sin secrets | Control de envío, dedupe y calidad comercial |
| Cron / Syncs | `automation_state`, logs | `api_sync_runs` para Tick/Daily | Salud del sistema y productividad de datos |
| Errores memoria | No centralizado | `data_memory_errors` | Diagnóstico sin bloquear app |

## Política de almacenamiento
- Memoria activada por defecto: `DATA_MEMORY_ENABLED=true`.
- Retención por defecto: 180 días general, 90 días cuotas, 30 días live, 90 días Telegram.
- No se guardan secrets, tokens, API keys ni passwords.
- JSON normalizado y recortado para evitar crecimiento enorme.
- La memoria nunca bloquea el flujo principal: si falla, registra error controlado y continúa.

## Advertencia API/legal
Esta memoria está pensada para funcionamiento interno, cache, análisis propio y mejora de SHARK. Antes de redistribuir datos históricos o vender raw data de terceros hay que revisar términos de The Odds API, TheSportsDB y cualquier proveedor usado. El producto debe vender análisis y valor derivado, no dumps brutos de API.
