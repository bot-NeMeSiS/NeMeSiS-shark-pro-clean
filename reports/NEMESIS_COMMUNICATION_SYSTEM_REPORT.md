# NeMeSiS Communication System Report

Fecha: 2026-07-30  
Estado: LOCAL_ONLY  
Producción: no modificada  
Envíos Telegram reales: 0  
Push/deploy/commit: no ejecutados

## Decisión ejecutiva

NeMeSiS dispone ahora de un sistema visual compartido para mensajes Telegram y previews administrativos. El cambio transforma el tono y la jerarquía de comunicación sin modificar la lógica de envío, scheduler, cron, cola, deduplicación, destinos, seguridad ni fuentes deportivas.

## Sistema visual creado

Identidad común:

- Cabecera: `🦈 NeMeSiS SHARK PRO`.
- Separador principal: `━━━━━━━━━━━━━━━━━━`.
- Separador secundario: `──────────────`.
- Bloques breves: Partido, Entrada, Contexto SHARK, Riesgo, Evidencia, Actualización y Limitaciones.
- Pie responsable: juego responsable, stake orientativo y ausencia de garantías.
- Transparencia: fuente, evidencia, calidad, frescura y limitaciones visibles cuando aplica.

## Mensajes rediseñados

| Tipo | Estado | Archivo | Nota |
|---|---|---|---|
| Picks | LOCAL_ONLY | `engines/telegram_message_formatter.py`, `engines/telegram_delivery_engine.py` | Jerarquía premium y riesgo visible. |
| Premium Pick | LOCAL_ONLY | `engines/telegram_message_formatter.py`, `engines/telegram_delivery_engine.py` | Mantiene cuota, mercado, selección, stake, confianza y contraargumento. |
| Partidos destacados | LOCAL_ONLY | `engines/telegram_message_formatter.py`, `engines/telegram_delivery_engine.py` | Agenda compacta, criterio SHARK y limitaciones. |
| Alertas Live | LOCAL_ONLY | `engines/telegram_message_formatter.py`, `engines/telegram_delivery_engine.py` | Cambio relevante, marcador y contexto sin simular tracking. |
| Resultados/finales | LOCAL_ONLY | `engines/telegram_message_formatter.py` | Cierre con marcador real y auditoría de pick si existe. |
| Recordatorios/previa | LOCAL_ONLY | `engines/telegram_message_formatter.py` | Partido en 60 minutos con hora Madrid. |
| Resumen diario/nocturno | LOCAL_ONLY | `engines/telegram_message_formatter.py`, `engines/telegram_delivery_engine.py` | Estado compacto y siguiente acción. |
| SHARK | LOCAL_ONLY | `engines/telegram_message_formatter.py`, `engines/telegram_intelligence_engine.py` | Análisis objetivo con evidencia y limitaciones. |
| Action Platform | LOCAL_ONLY | Plantillas reutilizables desde briefing/recap existentes | No se cambió la lógica de Action Platform. |
| Errores/estado sistema/admin | LOCAL_ONLY | `engines/telegram_delivery_engine.py` | Mensaje técnico controlado, no pick ni recomendación. |

## Garantías preservadas

- No se cambió `telegram_dedupe_key`.
- No se cambió scheduler.
- No se cambió cron.
- No se cambió cola ni estados de entrega.
- No se cambió destino configurado.
- No se cambió seguridad ni autenticación.
- No se hicieron llamadas externas.
- No se envió Telegram real.
- No se modificó Stripe.
- No se cambió versión.

## Archivos principales

- `engines/telegram_message_formatter.py`
- `engines/telegram_delivery_engine.py`
- `engines/telegram_intelligence_engine.py`
- `engines/sports_platform_contracts.py`
- `engines/project_operating_system_engine.py`
- `tests/test_telegram_premium_communication_system.py`

## Limitaciones

- Producción no certificada en este sprint.
- Telegram real no enviado en este sprint.
- El pytest completo queda PARTIAL por fallos de fixtures/base temporal no relacionados con Telegram: `/competition/140` sin tabla `competitions` y `/sports-hub` sin tabla `matches`.
- Las mejoras son de presentación de mensajes; no cambian frecuencia, selección, filtros ni negocio.
