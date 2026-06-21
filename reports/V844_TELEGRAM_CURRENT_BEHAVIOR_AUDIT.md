# V844 Telegram Current Behavior Audit

Base real usada: V843_PRODUCT_TEAM_COMMERCIAL_READY_FINAL_REVIEW.
Nueva versión: V844_TELEGRAM_TOP_PICK_QUALITY_CARDS_FILTER_FINAL.

## Hallazgo principal
Telegram ya tenía filtro de deporte y bloqueo básico de baja calidad, pero el canal público podía seguir aceptando candidatos de fútbol poco reconocibles si no había una señal clara de deporte no permitido. Eso permitía que ligas débiles, competiciones desconocidas o partidos con contexto insuficiente llegaran demasiado lejos en el flujo.

## Archivos revisados
- engines/telegram_sport_filter_engine.py
- engines/telegram_professional_scheduler.py
- engines/telegram_message_formatter.py
- engines/telegram_activity_engine.py
- app.py: master tick, scheduler, enqueue_daily_matches, enqueue_daily_picks, enqueue_auto_pick_alerts, enqueue_live_alerts, diagnostics.

## Causa
El filtro previo estaba enfocado a evitar deportes no fútbol y términos obvios como youth/reserve/regional, pero no calculaba una puntuación comercial conservadora ni aplicaba una política no-filler fuerte cuando solo había candidatos flojos.

## Corrección
Se crea engines/telegram_quality_filter_engine.py con scoring, explicación y filtrado conservador para Telegram público.
